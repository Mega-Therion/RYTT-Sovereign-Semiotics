"""Tests for DualPlaneGlyphTree rollups, 1r->2ry->3ryt->1R notation & bitemporal supersession."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from logos.glyphs import DualPlaneGlyphTree
from logos.layers import DeterministicSpectralEmbedder, EpistemicTier, LogosLayerCompiler


def _make_tree(fanout: int = 4) -> DualPlaneGlyphTree:
    compiler = LogosLayerCompiler(embedder=DeterministicSpectralEmbedder(dim=128), rank=4)
    return DualPlaneGlyphTree(compiler=compiler, fanout=fanout)


def test_fanout_guard_respects_vsa_snr_ceiling():
    compiler = LogosLayerCompiler(embedder=DeterministicSpectralEmbedder(dim=64))
    with pytest.raises(ValueError):
        DualPlaneGlyphTree(compiler=compiler, fanout=1)
    with pytest.raises(ValueError):
        DualPlaneGlyphTree(compiler=compiler, fanout=9)


def test_dual_plane_rollup_progression_and_level3():
    tree = _make_tree(fanout=4)
    expected = ["1r", "2ry", "3ryt", "1R", "1R+1r", "1R+2ry", "1R+3ryt", "2RY"]
    observed = []
    for idx in range(8):
        tree.append_episode(
            f"Episode {idx}: milestone marker MK_{idx:02d} verified.",
            epistemic_tier=EpistemicTier.P,
        )
        observed.append(tree.frontier_notation())
    assert observed == expected

    # Append 8 more (total 16) -> 4 Elevated glyphs roll up into 1 Super Level-3 glyph
    for idx in range(8, 16):
        tree.append_episode(f"Episode {idx}: marker MK_{idx:02d}.", epistemic_tier=EpistemicTier.P)
    assert tree.frontier_notation() == "1R^L3"

    # Verify Merkle integrity, Bloom superset containment, and drill-down
    integrity = tree.verify_integrity()
    assert integrity["valid"] is True, integrity
    assert integrity["acyclic"] is True
    assert integrity["bloom_checked"] == 20  # 4 L2 parents*4 + 1 L3 parent*4

    root_id = tree.active_frontier[0]
    children_l2 = tree.drill_down(root_id)
    assert len(children_l2) == 4
    assert all(c.level == 2 for c in children_l2)
    leaves = tree.get_leaves(root_id)
    assert len(leaves) == 16


def test_bitemporal_supersession_and_anti_glyph_isolation():
    tree = _make_tree(fanout=4)
    g0 = tree.append_episode("PORT=8080 initial", explicit_slots={"PORT": "8080"})
    tree.append_episode("PORT=9090 staging", explicit_slots={"PORT": "9090"})
    # Disproven Tier-F claim must NOT overwrite PORT truth table
    anti = tree.append_episode(
        "PORT=1337 broken claim",
        epistemic_tier=EpistemicTier.F,
        explicit_slots={"PORT": "1337"},
        anti_reason="Failed TLS check",
    )
    assert anti.glyph_id in tree.anti_glyphs
    g2 = tree.append_episode("PORT=18443 canonical", explicit_slots={"PORT": "18443"})

    truth = tree.active_truth_table()
    assert truth["PORT"]["value"] == "18443"
    assert truth["PORT"]["glyph_id"] == g2.glyph_id
    assert truth["PORT"]["revisions"] == 3
    assert "PORT" in g0.relational.superseded_slots

    restored = DualPlaneGlyphTree.from_dict(tree.to_dict(), compiler=tree.compiler)
    assert restored.active_truth_table()["PORT"]["value"] == "18443"
    assert restored.verify_integrity()["valid"] is True
