"""Known-key calibration scorer tests. Every key here is SYNTHETIC (generated below); nothing in
this file is evidence about any script."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/ancient_scripts/evaluation"))
import score_claims as sc  # noqa: E402

N = 2000  # fewer shuffles than the protocol's 10,000, to keep tests fast


def synthetic_key(n_signs=80, n_values=60, seed=1):
    rng = random.Random(seed)
    values = [f"v{i}" for i in range(n_values)]
    return {f"S{i:03d}": rng.choice(values) for i in range(n_signs)}


def test_perfect_method_passes_gate():
    key = synthetic_key()
    a = [{"sign": s, "value": v, "confidence": 0.95} for s, v in key.items()]
    r = sc.report(a, key, threshold=0.5, n_perm=N)
    assert r["hits"] == r["m"] == len(key)
    assert r["fdr"] == 0
    assert r["p_value"] < sc.GATE_P
    assert r["gate_pass"]


def test_random_method_fails_gate():
    key = synthetic_key()
    rng = random.Random(7)
    vals = sorted(set(key.values()))
    a = [{"sign": s, "value": rng.choice(vals), "confidence": 0.9} for s in key]
    r = sc.report(a, key, threshold=0.5, n_perm=N)
    assert r["fdr"] > 0.8
    assert r["p_value"] > 0.05
    assert not r["gate_pass"]


def test_permutation_null_is_not_trivial():
    key = synthetic_key()
    a = [{"sign": s, "value": v} for s, v in key.items()]
    r = sc.score(a, key, n_perm=N)
    # a perfect assertion set must sit far above the null: the null must actually shuffle
    assert r["null_mean"] < 0.25 * r["m"]
    assert r["null_q95"] < r["hits"]


def test_duplicate_sign_rejected():
    key = synthetic_key()
    a = [{"sign": "S001", "value": "v1"}, {"sign": "S001", "value": "v2"}]
    with pytest.raises(ValueError):
        sc.score(a, key, n_perm=10)


def test_unscorable_signs_excluded():
    key = {"A": "x", "B": "y"}
    a = [{"sign": "A", "value": "x"}, {"sign": "ZZ", "value": "q"}]
    r = sc.score(a, key, n_perm=50)
    assert r["m"] == 1 and r["unscorable"] == 1 and r["hits"] == 1


def test_threshold_drops_low_confidence_and_missing():
    key = {"A": "x", "B": "y", "C": "z"}
    a = [{"sign": "A", "value": "x", "confidence": 0.9}, {"sign": "B", "value": "q", "confidence": 0.4},
         {"sign": "C", "value": "z"}]
    r = sc.score(a, key, threshold=0.5, n_perm=50)
    assert r["m"] == 1 and r["hits"] == 1


def test_deterministic_with_seed():
    key = synthetic_key()
    a = [{"sign": s, "value": "v1"} for s in list(key)[:30]]
    assert sc.score(a, key, n_perm=500, seed=3) == sc.score(a, key, n_perm=500, seed=3)


def test_bad_input_rejected():
    with pytest.raises(ValueError):
        sc.score([{"sign": "A", "value": "x", "confidence": 1.5}], {"A": "x"}, n_perm=10)
    with pytest.raises(ValueError):
        sc.score([{"sign": "A"}], {"A": "x"}, n_perm=10)
