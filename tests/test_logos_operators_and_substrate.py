"""Tests for Horizon 1/2 operators, KVGlyphBank, .logos cartridges, CLI, MCP & benchmark."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pytest

from logos import LogosSession, run_logos_benchmark
from logos.layers import DeterministicSpectralEmbedder, LogosLayerCompiler
from logos.mcp_server import handle_jsonrpc_message
from logos.operators import Horizon2MatrixProjector, KVGlyphBank


def test_horizon2_projector_and_append_only_kv_prefix_preservation():
    compiler = LogosLayerCompiler(embedder=DeterministicSpectralEmbedder(dim=64), rank=4)
    g1 = compiler.compile_episode("First glyph block PORT=8080", glyph_id="g1_r_0000", slot_index=0)
    g2 = compiler.compile_episode("Second glyph block PORT=9090", glyph_id="g1_y_0001", slot_index=1)
    g3 = compiler.compile_episode("Third glyph block PORT=18443", glyph_id="g1_t_0002", slot_index=2)

    proj = Horizon2MatrixProjector(semantic_dim=64, model_dim=64, num_soft_tokens=4, num_layers=6, rank=4)
    soft = proj.project_soft_tokens(g1)
    assert soft.shape == (4, 64)
    kv1 = proj.compile_kv_glyph(g1)
    assert len(kv1) == 6
    assert kv1[0][0].shape == (4, 64)
    a_fw, b_fw = proj.compile_fast_weight_delta(g1)
    assert a_fw.shape == (64, 4) and b_fw.shape == (64, 4)

    # Gradient alignment step strictly reduces cosine loss
    loss_0 = proj.fit_reconstruction_step(g1, lr=0.2)
    loss_1 = proj.fit_reconstruction_step(g1, lr=0.2)
    assert loss_1 <= loss_0

    if importlib.util.find_spec("torch") is not None:
        t_out = proj.to_torch_tensors(g1)
        assert tuple(t_out["soft_tokens"].shape) == (4, 64)

    # Append-only KV bank keeps prefix bytes bit-for-bit identical across appends
    bank = KVGlyphBank(num_layers=6, max_slots=16)
    bank.allocate_slot(g1, proj.compile_kv_glyph(g1))
    fp_slot0 = bank.prefix_bytes_prefix_hash(1)
    bank.allocate_slot(g2, proj.compile_kv_glyph(g2))
    assert bank.prefix_bytes_prefix_hash(1) == fp_slot0
    fp_slot01 = bank.prefix_bytes_prefix_hash(2)
    bank.allocate_slot(g3, proj.compile_kv_glyph(g3))
    assert bank.prefix_bytes_prefix_hash(2) == fp_slot01
    assert bank.append_preservation_ratio() == 1.0


def test_cartridge_export_verify_reload_and_tamper_rejection(tmp_path: Path):
    db_path = tmp_path / "session.db"
    session = LogosSession.from_db(db_path, context_budget_tokens=200)
    session.orchestrator.watermark_ratio = 0.65
    session.orchestrator.splitter.min_episode_tokens = 25

    for idx in range(5):
        session.ingest(
            "system",
            f"Wave {idx} marker NEEDLE_ZX_{idx} active_mode=v{idx} " + ("telemetry_pad " * 18),
            explicit_slots={"ACTIVE_MODE": f"v{idx}"},
        )
    session.force_flush()

    cart_path = session.export_cartridge(tmp_path / "snapshot.logos")
    assert cart_path.exists()
    ver = LogosSession.verify_cartridge(cart_path)
    assert ver["valid"] is True, ver

    reloaded = LogosSession.from_cartridge(cart_path)
    frame = reloaded.compose("Check NEEDLE_ZX_0 and ACTIVE_MODE", max_tokens=200)
    assert "NEEDLE_ZX_0" in frame.rendered_text
    assert frame.active_truth_table["ACTIVE_MODE"]["value"] == "v4"
    session.close()
    reloaded.close()


def test_cli_and_mcp_jsonrpc_end_to_end(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    env_python = sys.executable

    # 1. `logos demo` CLI subprocess
    demo_proc = subprocess.run(
        [env_python, "-m", "logos._cli", "demo"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert demo_proc.returncode == 0, demo_proc.stderr
    demo_out = json.loads(demo_proc.stdout)
    assert demo_out["active_truth"]["CANONICAL_PORT"]["value"] == "18443"
    assert demo_out["bloom_hits"]

    # 2. Persistent SQLite ingest -> compose -> export -> verify workflow via CLI
    db_file = tmp_path / "cli.db"
    cart_file = tmp_path / "cli_out.logos"
    r1 = subprocess.run(
        [env_python, "-m", "logos._cli", "ingest", "--db", str(db_file), "CLI_NEEDLE_ALPHA=active"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r1.returncode == 0, r1.stderr

    r2 = subprocess.run(
        [env_python, "-m", "logos._cli", "export", "--db", str(db_file), str(cart_file)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r2.returncode == 0, r2.stderr

    r3 = subprocess.run(
        [env_python, "-m", "logos._cli", "verify", str(cart_file)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r3.returncode == 0, r3.stderr
    assert json.loads(r3.stdout)["valid"] is True

    # 3. MCP JSON-RPC 2.0 wire handling
    mcp_session = LogosSession(context_budget_tokens=200)
    init_resp = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, mcp_session)
    assert init_resp["result"]["serverInfo"]["name"] == "logos-mcp"
    list_resp = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, mcp_session)
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    assert {
        "logos_ingest_turn",
        "logos_compose_viewport",
        "logos_hydrate_glyph",
        "logos_register_anti_glyph",
        "logos_status",
        "logos_export_cartridge",
    } <= tool_names

    call_resp = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "logos_ingest_turn", "arguments": {"content": "MCP_TOKEN_77 verified"}},
        },
        mcp_session,
    )
    assert call_resp["result"]["isError"] is False
    mcp_session.close()


def test_logos_benchmark_beats_sliding_and_prose_baselines():
    report = run_logos_benchmark(use_ollama=False)
    assert report["tree_integrity_valid"] is True
    assert report["baselines"]["logos"]["exact_needle_recall"] == 1.0
    assert report["baselines"]["logos"]["supersession_accuracy"] == 1.0
    assert report["baselines"]["logos"]["anti_glyph_recall"] == 1.0
    assert (
        report["baselines"]["logos"]["exact_needle_recall"]
        > report["baselines"]["sliding_window"]["exact_needle_recall"]
    )
    assert (
        report["baselines"]["logos"]["exact_needle_recall"]
        > report["baselines"]["prose_compaction"]["exact_needle_recall"]
    )
    assert report["kv_bank"]["append_preservation_ratio"] == 1.0
    assert report["vsa_snr_check"]["int32_step0_similarity"] > 0.56
