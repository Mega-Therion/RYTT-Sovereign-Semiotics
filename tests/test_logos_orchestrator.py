"""Tests for LogosOrchestrator: semantic split, hot tail, Bloom MMU prefetch & fail-closed hydrate."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from logos.layers import DeterministicSpectralEmbedder, EpistemicTier
from logos.orchestrator import LogosOrchestrator
from logos.substrate import LogosSubstrate


def test_rolling_crystallization_hot_tail_and_hierarchical_bloom_prefetch():
    substrate = LogosSubstrate(":memory:")
    orch = LogosOrchestrator(
        substrate=substrate,
        embedder=DeterministicSpectralEmbedder(dim=128),
        fanout=4,
        context_budget_tokens=260,
        watermark_ratio=0.70,
        hot_tail_ratio=0.22,
        prefetch_budget_ratio=0.35,
        min_episode_tokens=30,
        max_episode_tokens=110,
    )

    pad = "routine telemetry metrics healthy across cluster nodes " * 6
    orch.ingest_turn(
        "system",
        "Critical boot anomaly ERR_9481_QUARTZ observed on node7. CANONICAL_PORT=8080. " + pad,
        epistemic_tier=EpistemicTier.D,
        explicit_slots={"CANONICAL_PORT": "8080"},
    )
    for i in range(2, 8):
        slots = {"CANONICAL_PORT": "18443"} if i == 5 else {}
        orch.ingest_turn("assistant", f"Step {i} continuation: CANONICAL_PORT stabilized. " + pad, explicit_slots=slots)

    orch.force_flush()
    assert orch.active_turns, "20% verbatim hot tail must never be empty"
    assert len(orch.tree.nodes) >= 4
    # Frontier rolled up at least once into Elevated plane
    assert any(g.level >= 2 for g in orch.tree.frontier_glyphs()) or len(orch.tree.frontier_glyphs()) >= 2

    # Rare Epoch-1 symbol buried inside Elevated parent MUST auto-prefetch via hierarchical Bloom MMU!
    frame = orch.compose_viewport("Please investigate ERR_9481_QUARTZ right away", max_tokens=260)
    assert frame.total_tokens <= 260
    assert frame.bloom_hits, "Bloom MMU should trigger on Elevated/Ground frontier"
    assert "ERR_9481_QUARTZ" in frame.rendered_text
    assert frame.lod0_hydrated
    assert frame.active_truth_table["CANONICAL_PORT"]["value"] == "18443"


def test_fail_closed_sha256_tamper_detection_on_hydrate():
    substrate = LogosSubstrate(":memory:")
    orch = LogosOrchestrator(
        substrate=substrate,
        embedder=DeterministicSpectralEmbedder(dim=128),
        fanout=4,
        context_budget_tokens=180,
        watermark_ratio=0.65,
        hot_tail_ratio=0.20,
        min_episode_tokens=20,
        max_episode_tokens=80,
    )
    orch.ingest_turn("user", "Immutable theorem anchor PROOF_X_42 verified " * 12, epistemic_tier=EpistemicTier.D)
    orch.ingest_turn("user", "Tail turn kept verbatim " * 6, epistemic_tier=EpistemicTier.P)
    orch.force_flush()

    leaf = orch.tree.get_leaves()[0]
    ok_slice = orch.hydrate(leaf.glyph_id, query="PROOF_X_42")
    assert ok_slice.verified_sha256 is True
    assert "PROOF_X_42" in ok_slice.content

    # Simulate silent DB corruption / tampering -> hydrate MUST fail closed with ValueError
    substrate._conn.execute(
        "UPDATE raw_blocks SET content = 'TAMPERED PAYLOAD' WHERE raw_sha256 = ?",
        (leaf.provenance.raw_sha256,),
    )
    substrate._conn.commit()
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        orch.hydrate(leaf.glyph_id)
