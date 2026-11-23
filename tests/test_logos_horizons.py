"""Comprehensive tests for L.O.G.O.S. Horizons 1–3 (v0.2 -> v0.4)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from logos import (
    DualPlaneGlyphTree,
    EpistemicTier,
    GlyphConditionedAttentionLM,
    LogosLayerCompiler,
    LogosSession,
    NaturalLanguageDeltaExtractor,
    OllamaStateDeltaExtractor,
    RelationType,
    TorchMatrixGlyphProjector,
    build_unstructured_long_horizon_workload,
    merge_cartridges,
    run_long_horizon_eval,
    train_projector_on_glyphs,
    verify_cartridge,
)
from logos.layers import DeterministicSpectralEmbedder
from logos.layers.delta_extractor import _SLOT_KV_RE
from logos.mcp_server import handle_jsonrpc_message


def test_horizon1_natural_language_and_ollama_delta_extractor():
    extractor = NaturalLanguageDeltaExtractor()

    prose = (
        "During staging we moved the gateway port from 8080 to 9090. "
        "After the mTLS audit we ditched port 9090 and moved the gateway to 18443. "
        "We deprecated tools/old_gate.py and now use 1_engine/tools/check_claim_gate.py for the gate script. "
        "We settled on append_only_pages for the kv strategy, and the proof tier is now D. "
        "Module theorem_rytt_holonomy_v2 depends on 1_engine/tools/check_claim_gate.py. "
        "We disproved NEG_BRANCH_EULER_GAUGE because naive disformal coupling breaks luminal speed bounds."
    )
    res = extractor.extract(prose, glyph_id="g1_r_0000")

    assert res.slots["GATEWAY_PORT"] == "18443"
    assert res.supersessions["GATEWAY_PORT"] == "9090"
    assert res.slots["GATE_SCRIPT"] == "1_engine/tools/check_claim_gate.py"
    assert res.supersessions["GATE_SCRIPT"] == "tools/old_gate.py"
    assert res.slots["KV_STRATEGY"] == "append_only_pages"
    assert res.slots["PROOF_TIER"] == "D"

    rel_types = {e.relation for e in res.relations}
    assert RelationType.SUPERSEDES in rel_types
    assert RelationType.DEPENDS_ON in rel_types
    assert RelationType.REFUTES in rel_types
    assert any(ac["claim"] == "NEG_BRANCH_EULER_GAUGE" for ac in res.anti_claims)

    # Verify OllamaStateDeltaExtractor falls back cleanly when pointed at an offline port
    ollama_ext = OllamaStateDeltaExtractor(
        model="qwen2.5:1.5b",
        base_url="http://127.0.0.1:19",
        timeout=0.2,
    )
    fallback_res = ollama_ext.extract(prose, glyph_id="g1_r_0000")
    assert ollama_ext.last_fallback is True
    assert fallback_res.slots["GATEWAY_PORT"] == "18443"
    assert fallback_res.slots["GATE_SCRIPT"] == "1_engine/tools/check_claim_gate.py"


def test_horizon1_sleep_consolidate_improves_semantic_coherence_and_preserves_invariants():
    embedder = DeterministicSpectralEmbedder(dim=128)
    compiler = LogosLayerCompiler(embedder=embedder, rank=4, use_nl_extractor=True)
    tree = DualPlaneGlyphTree(compiler=compiler, fanout=4)

    # Append 8 interleaved episodes alternating between Topic A (quantum holonomy) and Topic B (SQLite storage)
    for idx in range(8):
        if idx % 2 == 0:
            text = (
                f"Quantum holonomy theorem wave {idx}: Berry phase parallel transport across "
                f"Z22 cyclic lattice manifold verified symplectic gauge invariance. "
                + ("quantum_holonomy_lattice_berry_phase " * 8)
            )
            if idx == 0:
                text += " We bound the gateway port to 8080."
            elif idx == 4:
                text += " We moved the gateway port from 8080 to 18443."
        else:
            text = (
                f"SQLite WAL b-tree replication wave {idx}: checkpointed FTS5 inverted index pages "
                f"and verified fsync durability across NVMe disk sectors. "
                + ("sqlite_wal_btree_fts5_nvme_checkpoint " * 8)
            )
        tree.append_episode(text, epistemic_tier=EpistemicTier.D)

    leaves_before = {lf.glyph_id: lf.provenance.raw_sha256 for lf in tree.get_leaves()}
    truth_before = tree.active_truth_table()
    assert truth_before["GATEWAY_PORT"]["value"] == "18443"

    report = tree.sleep_consolidate()
    assert report["consolidated"] is True
    assert report["leaf_count"] == 8
    assert report["raw_sha256_preserved"] is True
    assert report["truth_slots_preserved"] is True
    assert report["integrity"]["valid"] is True
    assert report["mean_intra_cluster_cosine_after"] > report["mean_intra_cluster_cosine_before"]
    assert report["coherence_gain"] > 0.15

    leaves_after = {lf.glyph_id: lf.provenance.raw_sha256 for lf in tree.get_leaves()}
    assert leaves_after == leaves_before
    assert tree.active_truth_table() == truth_before


def test_horizon1_unstructured_long_horizon_eval_zero_kv_strings():
    workload = build_unstructured_long_horizon_workload()
    for ep in workload["episodes"]:
        kv_matches = _SLOT_KV_RE.findall(ep["text"])
        assert kv_matches == [], f"Found artificial KEY=VALUE token in natural prose workload: {kv_matches}"

    report = run_long_horizon_eval(use_ollama=False, budget_tokens=1100, consolidate=True)
    assert report["zero_artificial_kv_tokens"] is True
    assert report["tree_integrity_valid"] is True
    assert report["sleep_consolidation"]["consolidated"] is True
    assert report["sleep_consolidation"]["integrity"]["valid"] is True

    logos_metrics = report["baselines"]["logos"]
    sw_metrics = report["baselines"]["sliding_window"]
    pr_metrics = report["baselines"]["prose_compaction"]

    assert logos_metrics["exact_needle_recall"] == 1.0
    assert logos_metrics["nl_supersession_accuracy"] == 1.0
    assert logos_metrics["anti_glyph_recall"] == 1.0
    assert logos_metrics["exact_needle_recall"] > sw_metrics["exact_needle_recall"]
    assert logos_metrics["exact_needle_recall"] > pr_metrics["exact_needle_recall"]
    assert logos_metrics["nl_supersession_accuracy"] > sw_metrics["nl_supersession_accuracy"]


def test_horizon2_torch_projector_and_attention_lm_zero_token_bypass():
    embedder = DeterministicSpectralEmbedder(dim=64)
    compiler = LogosLayerCompiler(embedder=embedder, rank=4, use_nl_extractor=True)
    tree = DualPlaneGlyphTree(compiler=compiler, fanout=4)

    episodes = [
        "We bound the gateway port to 8080 and observed ERR_9481_QUARTZ during cold boot.",
        "Stack diagnostics pinned misaligned pointer 0xdeadbeef42cafe in spectral bridge.",
        "We deprecated tools/old_gate.py and now use 1_engine/tools/check_claim_gate.py for the gate script.",
        "After the mTLS audit we ditched port 8080 and moved the gateway to 18443.",
    ]
    for text in episodes:
        tree.append_episode(text, epistemic_tier=EpistemicTier.D)

    glyphs = [tree.nodes[gid] for gid in sorted(tree.nodes.keys())]

    # Test single-glyph projection and direct attention LM conditioning
    projector = TorchMatrixGlyphProjector(
        semantic_dim=64,
        hidden_dim=64,
        num_soft_tokens=4,
        num_layers=6,
        num_heads=4,
        rank=4,
    )
    bundle = projector.project(glyphs[0])
    assert bundle.inputs_embeds.shape == (1, 4, 64)
    assert len(bundle.past_key_values) == 6
    assert bundle.past_key_values[0][0].shape == (1, 4, 4, 16)
    assert bundle.fast_weight_a.shape == (1, 64, 4)
    assert bundle.fast_weight_b.shape == (1, 64, 4)

    lm = GlyphConditionedAttentionLM(vocab_size=64, hidden_dim=64, num_layers=6, num_heads=4)
    out = lm.forward(bundle, query_token_ids=[3, 14, 15, 9])
    assert out["logits"].shape == (4, 64)
    assert out["archived_text_tokens_used"] == 0
    assert out["soft_prefix_tokens_used"] == 4

    # Train in pure-NumPy mode and verify convergence + KV prefix invariance
    np_metrics = train_projector_on_glyphs(
        glyphs=glyphs,
        epochs=25,
        lr=0.08,
        hidden_dim=64,
        num_soft_tokens=4,
        num_layers=6,
        num_heads=4,
        vocab_size=64,
        prefer_torch=False,
    )
    assert np_metrics["backend"] == "numpy"
    assert np_metrics["archived_text_tokens_tokenized"] == 0
    assert np_metrics["kv_prefix_byte_invariance"] is True
    assert np_metrics["final_total_loss"] < np_metrics["initial_total_loss"]
    assert np_metrics["final_perplexity"] < np_metrics["initial_perplexity"]
    assert np_metrics["final_semantic_cosine"] > np_metrics["initial_semantic_cosine"]

    # Subprocess execution of scripts/train_logos_projector.py
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "train_logos_projector.py"), "--epochs", "20", "--hidden-dim", "64"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    script_out = json.loads(proc.stdout)
    assert script_out["archived_text_tokens_tokenized"] == 0
    assert script_out["kv_prefix_byte_invariance"] is True
    assert script_out["final_total_loss"] < script_out["initial_total_loss"]


def test_horizon3_cartridge_bus_bitemporal_crdt_merge(tmp_path: Path):
    # Agent A session
    sess_a = LogosSession(db_path=tmp_path / "agent_a.db", context_budget_tokens=220, fanout=4)
    sess_a.orchestrator.watermark_ratio = 0.65
    sess_a.orchestrator.splitter.min_episode_tokens = 20

    pad = "distributed cluster telemetry nominal " * 12
    shared_turn = "Shared foundation turn: ERR_9481_QUARTZ logged during cold boot. " + pad
    sess_a.ingest("system", shared_turn, epistemic_tier=EpistemicTier.D)
    sess_a.ingest(
        "assistant",
        "Agent A set the gateway port to 8080 and verified proof tier D for the holonomy module. " + pad,
        epistemic_tier=EpistemicTier.D,
        explicit_slots={"GATEWAY_PORT": "8080", "HOLONOMY_TIER": "verified_D"},
    )
    sess_a.register_anti_glyph("NEG_BRANCH_ALPHA disproven by Agent A", reason="Breaks gauge symmetry")
    sess_a.force_flush()
    cart_a = sess_a.export_cartridge(tmp_path / "agent_a.logos")
    sess_a.close()

    # Agent B session (shares foundation raw block, updates GATEWAY_PORT to 18443 at tier D,
    # and proposes a lower-tier [O] speculation on HOLONOMY_TIER that must NOT override Agent A's [D] truth)
    sess_b = LogosSession(db_path=tmp_path / "agent_b.db", context_budget_tokens=220, fanout=4)
    sess_b.orchestrator.watermark_ratio = 0.65
    sess_b.orchestrator.splitter.min_episode_tokens = 20

    sess_b.ingest("system", shared_turn, epistemic_tier=EpistemicTier.D)
    sess_b.ingest(
        "assistant",
        "Agent B switched the gateway port from 8080 to 18443 after mTLS rollout. " + pad,
        epistemic_tier=EpistemicTier.D,
        explicit_slots={"GATEWAY_PORT": "18443"},
    )
    sess_b.ingest(
        "user",
        "Agent B unverified speculation on holonomy tier. " + pad,
        epistemic_tier=EpistemicTier.O,
        explicit_slots={"HOLONOMY_TIER": "speculative_O"},
    )
    sess_b.register_anti_glyph("NEG_BRANCH_BETA disproven by Agent B", reason="Induces 2^-t signal decay")
    sess_b.force_flush()
    cart_b = sess_b.export_cartridge(tmp_path / "agent_b.logos")
    sess_b.close()

    merged_path = tmp_path / "merged_council.logos"
    merge_report = merge_cartridges(cart_a, cart_b, merged_path, consolidate=True)

    assert merge_report["valid"] is True
    assert merge_report["raw_blocks_deduplicated"] >= 1
    assert merge_report["anti_glyphs_merged"] == 2
    assert merge_report["conflicts_resolved"] >= 2

    # Newer [D] GATEWAY_PORT=18443 wins over older [D] 8080;
    # Higher-tier [D] HOLONOMY_TIER="verified_D" wins over newer lower-tier [O] "speculative_O"!
    truth = merge_report["active_truth_table"]
    assert truth["GATEWAY_PORT"]["value"] == "18443"
    assert truth["HOLONOMY_TIER"]["value"] == "verified_D"
    assert truth["HOLONOMY_TIER"]["epistemic_tier"] == "D"

    ver = verify_cartridge(merged_path)
    assert ver["valid"] is True, ver

    merged_session = LogosSession.from_cartridge(merged_path)
    hist = merged_session.query_truth_history("GATEWAY_PORT")
    assert hist["revisions"] >= 2
    assert hist["active"]["value"] == "18443"
    merged_session.close()


def test_horizon3_cli_mcp_and_static_hud_audit(tmp_path: Path):
    db_a = tmp_path / "s1.db"
    db_b = tmp_path / "s2.db"
    cart_a = tmp_path / "c1.logos"
    cart_b = tmp_path / "c2.logos"
    cart_m = tmp_path / "cm.logos"
    hud_json = tmp_path / "hud.json"

    s1 = LogosSession.from_db(db_a, context_budget_tokens=180)
    s1.orchestrator.watermark_ratio = 0.65
    s1.orchestrator.splitter.min_episode_tokens = 20
    for i in range(4):
        s1.ingest(
            "system",
            f"Episode {i}: bound the gateway port to {8080 + i} and checked ERR_9481_QUARTZ. " + ("pad_word " * 18),
        )
    s1.force_flush()
    s1.export_cartridge(cart_a)
    s1.close()

    s2 = LogosSession.from_db(db_b, context_budget_tokens=180)
    s2.orchestrator.watermark_ratio = 0.65
    s2.orchestrator.splitter.min_episode_tokens = 20
    s2.ingest(
        "assistant",
        "We ditched port 8083 and moved the gateway to 18443 across production nodes. " + ("pad_word " * 20),
        epistemic_tier=EpistemicTier.D,
    )
    s2.force_flush()
    s2.export_cartridge(cart_b)
    s2.close()

    # Test CLI: consolidate, history, hud-export, merge, long-eval
    for cmd in (
        [sys.executable, "-m", "logos._cli", "consolidate", "--db", str(db_a)],
        [sys.executable, "-m", "logos._cli", "history", "--db", str(db_a), "--key", "GATEWAY_PORT"],
        [sys.executable, "-m", "logos._cli", "hud-export", "--db", str(db_a), "--out", str(hud_json)],
        [sys.executable, "-m", "logos._cli", "merge", str(cart_a), str(cart_b), str(cart_m), "--consolidate"],
        [sys.executable, "-m", "logos._cli", "long-eval", "--budget", "1100"],
    ):
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Command {cmd} failed: {proc.stderr}"

    assert hud_json.exists()
    hud_data = json.loads(hud_json.read_text(encoding="utf-8"))
    assert hud_data["format"] == "logos-hud-telemetry"
    assert hud_data["tree_integrity"]["valid"] is True

    # Test MCP tools: logos_sleep_consolidate, logos_query_truth_history, logos_export_hud_json, logos_merge_cartridges
    mcp_sess = LogosSession.from_db(db_a)
    list_resp = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, mcp_sess)
    names = {t["name"] for t in list_resp["result"]["tools"]}
    assert {
        "logos_merge_cartridges",
        "logos_sleep_consolidate",
        "logos_query_truth_history",
        "logos_export_hud_json",
    } <= names

    for idx, (t_name, t_args) in enumerate(
        [
            ("logos_sleep_consolidate", {}),
            ("logos_query_truth_history", {"key": "GATEWAY_PORT"}),
            ("logos_export_hud_json", {"output_path": str(tmp_path / "mcp_hud.json")}),
            (
                "logos_merge_cartridges",
                {"path_a": str(cart_a), "path_b": str(cart_b), "output_path": str(tmp_path / "mcp_merged.logos")},
            ),
        ],
        start=10,
    ):
        resp = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": idx, "method": "tools/call", "params": {"name": t_name, "arguments": t_args}},
            mcp_sess,
        )
        assert resp["result"]["isError"] is False, resp
    mcp_sess.close()

    # Static site accessibility audit including web/logos-hud.html
    audit_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_static_site.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert audit_proc.returncode == 0, audit_proc.stdout + audit_proc.stderr
    assert "4 routes" in audit_proc.stdout
