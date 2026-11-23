"""Tests verifying the exact int32 VSAAccumulator fix against 2^{-t} forgetting."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from rytt.vsa import HV, HolonomicVSATracker, VSAAccumulator, superpose


def test_vsa_accumulator_equal_weight_and_merge():
    hvs = [HV.from_seed(f"item_{i}") for i in range(9)]
    acc_full = VSAAccumulator()
    acc_full.add_many(hvs)
    assert len(acc_full) == 9

    acc_a = VSAAccumulator()
    acc_a.add_many(hvs[:4])
    acc_b = VSAAccumulator()
    acc_b.add_many(hvs[4:])
    merged = acc_a.merge(acc_b)

    assert len(merged) == 9
    assert merged.to_hv() == acc_full.to_hv()
    # Exact equivalence with flat majority vote over odd set size
    assert merged.to_hv() == superpose(hvs)


def test_vsa_accumulator_roundtrip_serialization():
    acc = VSAAccumulator()
    acc.add_many([HV.from_seed(f"ser_{i}") for i in range(5)])
    raw = acc.to_bytes()
    restored = VSAAccumulator.from_bytes(raw)
    assert len(restored) == 5
    assert restored.to_hv() == acc.to_hv()

    with pytest.raises(ValueError):
        VSAAccumulator.from_bytes(b"short")


def test_holonomic_tracker_step0_survives_25_steps():
    tracker = HolonomicVSATracker()
    first = tracker.encode_step("genesis_anchor_constraint_alpha")
    for idx in range(1, 25):
        tracker.encode_step(f"incremental_step_{idx}_payload")

    retrieved_0 = tracker.retrieve_step(0)
    retrieved_last = tracker.retrieve_step(24)
    assert retrieved_0 is not None
    assert retrieved_last is not None
    # With equal unit weights across 25 items, binomial SNR keeps similarity well above 0.57
    sim_0 = retrieved_0.similarity(first)
    sim_24 = retrieved_last.similarity(HV.from_seed(b"incremental_step_24_payload"))
    assert sim_0 > 0.56, f"Step 0 suffered forgetting: sim={sim_0}"
    assert abs(sim_0 - sim_24) < 0.05, f"Step weighting skewed: step0={sim_0}, step24={sim_24}"

    # Verify naive pairwise superpose DOES suffer forgetting (step 0 near random 0.50)
    idx0 = HV.from_seed("step_0")
    legacy = idx0 ^ first
    for idx in range(1, 25):
        sv = HV.from_seed(f"step_{idx}") ^ HV.from_seed(f"incremental_step_{idx}_payload")
        legacy = superpose([legacy, sv])
    legacy_sim_0 = idx0.unbind(legacy).similarity(first)
    assert sim_0 > legacy_sim_0 + 0.04
