"""Tests for L.O.G.O.S. Layer 1/2/3 Tensor-Glyph compilation and 10,240-bit Bloom MMU."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from logos.layers import (
    BLOOM_BYTES,
    BloomFilter10240,
    BloomMMU,
    DeterministicSpectralEmbedder,
    EpistemicTier,
    LogosLayerCompiler,
    TensorGlyph,
    extract_entities,
)


def test_bloom_filter_10240_zero_false_negatives_and_low_fpr():
    flt = BloomFilter10240()
    inserted = [f"ERR_{i:04d}_QUARTZ" for i in range(120)]
    flt.add_many(inserted)
    assert len(flt.to_bytes()) == BLOOM_BYTES
    assert all(flt.might_contain(tok) for tok in inserted)

    # Probe 500 absent entities -> empirical FPR < 1%
    false_positives = sum(1 for i in range(500) if flt.might_contain(f"ABSENT_SYMBOL_{i}"))
    assert false_positives / 500.0 < 0.01

    flt2 = BloomFilter10240()
    flt2.add("0xdeadbeef42cafe")
    unioned = BloomFilter10240.union([flt, flt2])
    assert unioned.is_superset_of(flt)
    assert unioned.is_superset_of(flt2)
    assert unioned.might_contain("0xdeadbeef42cafe")
    assert unioned.might_contain("ERR_0000_QUARTZ")

    restored = BloomFilter10240.from_bytes(unioned.to_bytes())
    assert restored.bit_count() == unioned.bit_count()


def test_extract_entities_captures_rare_identifiers():
    sample = (
        "Failure ERR_9481_QUARTZ at 0xdeadbeef42cafe in 1_engine/tools/check_claim_gate.py "
        "(digest sha256:9f86d081884c, PUA U+E011, endpoint port:18443, theorem_rytt_holonomy_v2)."
    )
    ents = extract_entities(sample)
    for expected in (
        "ERR_9481_QUARTZ",
        "0xdeadbeef42cafe",
        "1_engine/tools/check_claim_gate.py",
        "sha256:9f86d081884c",
        "U+E011",
        "port:18443",
        "theorem_rytt_holonomy_v2",
    ):
        assert expected in ents, f"Missing entity {expected!r} in {ents}"


def test_compile_episode_and_epistemic_quarantine():
    embedder = DeterministicSpectralEmbedder(dim=128)
    compiler = LogosLayerCompiler(embedder=embedder, rank=4)
    glyph = compiler.compile_episode(
        episode_text="CANONICAL_PORT=18443; ERR_4912 detected in check_claim_gate.py",
        glyph_id="g1_r_0000",
        slot_index=0,
        plane="Ground",
        level=1,
        epistemic_tier=EpistemicTier.D,
    )
    assert glyph.symbol == "r"
    assert glyph.rytt_pua == "\uE011"
    assert glyph.geometric_vec.shape == (22,)
    assert glyph.relational.active_slots["CANONICAL_PORT"] == "18443"

    # Layer 2 rank-r operator steers query cleanly and preserves shape
    q, _ = embedder.embed("CANONICAL_PORT")
    steered = glyph.relational.apply(q)
    assert steered.shape == (128,)
    assert abs(float(np.linalg.norm(steered)) - 1.0) < 1e-4

    # Serialization round-trip + deterministic digest
    restored = TensorGlyph.from_dict(glyph.to_dict())
    assert restored.content_digest() == glyph.content_digest()
    assert np.allclose(restored.semantic.vector, glyph.semantic.vector, atol=1e-6)

    # Tier F quarantine must NEVER populate live active_slots
    bad = compiler.compile_episode(
        episode_text="CANONICAL_PORT=999999 fabricated port",
        glyph_id="anti_0000",
        slot_index=0,
        epistemic_tier=EpistemicTier.F,
        anti_reason="falsified claim",
    )
    assert bad.is_anti_glyph is True
    assert bad.relational.active_slots == {}

    mmu = BloomMMU()
    hits, us = mmu.match_query("Diagnose ERR_4912 right now", [glyph])
    assert hits and hits[0].glyph_id == "g1_r_0000"
    assert us >= 0.0
