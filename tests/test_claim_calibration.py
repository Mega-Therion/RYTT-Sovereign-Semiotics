"""Known-key calibration scorer tests (protocol v0.1.1). Every key here is SYNTHETIC (generated below);
nothing in this file is evidence about any script."""
import hashlib
import json
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


def unique_key(k):
    return {f"S{i:04d}": f"v{i}" for i in range(k)}


def test_perfect_method_passes_gate():
    key = synthetic_key()
    a = [{"sign": s, "value": v, "confidence": 0.95} for s, v in key.items()]
    r = sc.score(a, key, threshold=0.5, n_perm=N)
    assert r["hits"] == r["m"] == len(key) and r["fdr"] == 0
    assert sc.gate(r)


def test_two_of_two_no_longer_passes():
    # v0.1.0 passed this at K=87 (p=0.0003); the red team's blocking finding 1
    r = sc.score([{"sign": "S0001", "value": "v1"}, {"sign": "S0002", "value": "v2"}], unique_key(87), n_perm=N)
    assert r["fdr"] == 0 and r["fdr_upper95"] > sc.GATE_FDR_UPPER
    assert not sc.gate(r)


def test_minimum_m_at_zero_errors_is_14():
    key = unique_key(200)
    a = [{"sign": s, "value": v} for s, v in list(key.items())]
    assert sc.clopper_pearson_upper(0, 13) > sc.GATE_FDR_UPPER >= sc.clopper_pearson_upper(0, 14)
    assert not sc.gate(sc.score(a[:13], key, n_perm=N))
    assert sc.gate(sc.score(a[:14], key, n_perm=N))


def test_key_padding_does_not_help():
    # v0.1.0: one correct assertion failed at K=87 and passed at K=187
    a = [{"sign": "S0001", "value": "v1"}]
    assert sc.score(a, unique_key(87), n_perm=N)["p_value"] == sc.score(a, unique_key(187), n_perm=N)["p_value"]


def test_key_order_does_not_change_p():
    key = unique_key(100)
    a = [{"sign": s, "value": v} for s, v in list(key.items())[:20]]
    items = list(key.items())
    random.Random(5).shuffle(items)
    assert sc.score(a, key, n_perm=N) == sc.score(a, dict(items), n_perm=N)


def test_random_method_fails_gate():
    key = synthetic_key()
    rng = random.Random(7)
    vals = sorted(set(key.values()))
    a = [{"sign": s, "value": rng.choice(vals), "confidence": 0.9} for s in key]
    r = sc.score(a, key, threshold=0.5, n_perm=N)
    assert r["fdr"] > 0.8 and not sc.gate(r)


def test_modal_value_method_fails_gate():
    key = synthetic_key()
    modal = max(set(key.values()), key=list(key.values()).count)
    r = sc.score([{"sign": s, "value": modal} for s in key], key, n_perm=N)
    assert r["p_value"] == 1.0 and not sc.gate(r)


def test_frequency_rank_baseline_fails_gate_on_zipf_control():
    rng = random.Random(11)
    values = [f"v{i}" for i in range(40)]
    weights = [1 / (i + 1) for i in range(40)]
    key = {f"S{i:03d}": rng.choices(values, weights)[0] for i in range(120)}
    corpus = [s for s in key for _ in range(rng.randint(1, 30))]
    sign_counts = {s: corpus.count(s) for s in key}
    value_counts = {v: sum(c for s, c in sign_counts.items() if key[s] == v) for v in values}
    base = sc.frequency_rank_baseline(sign_counts, value_counts)
    r = sc.score(base, key, n_perm=N)
    assert not sc.gate(r)


def test_method_must_beat_the_baseline():
    key = unique_key(100)
    a = [{"sign": s, "value": v} for s, v in key.items()]
    r = sc.score(a, key, n_perm=N)
    assert sc.gate(r, baseline={"fdr": 0.5})
    assert not sc.gate(r, baseline={"fdr": 0.0})


def test_normalization_and_alternatives():
    import unicodedata
    key = {"A": "KO", "B": "ḫa", "C": ["a2", "ha"]}
    a = [{"sign": "A", "value": " ko "}, {"sign": "B", "value": unicodedata.normalize("NFD", "ḫa")},
         {"sign": "C", "value": "HA"}]
    assert sc.score(a, key, n_perm=50)["hits"] == 3


def test_bad_inputs_rejected():
    key = {"A": "x"}
    for bad in ([{"sign": "A", "value": "x", "confidence": True}], [{"sign": "A", "value": "x", "confidence": 1.5}],
                [{"sign": "A"}], [{"sign": "A", "value": "x"}, {"sign": "A", "value": "y"}],
                [{"sign": "ZZ", "value": "x"}]):
        with pytest.raises(sc.BadInput):
            sc.score(bad, key, n_perm=10)
    with pytest.raises(sc.BadInput):
        sc.score([{"sign": "A", "value": "x"}], {"A": 3}, n_perm=10)


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj))
    return p


def test_declaration_required_checked_and_logged(tmp_path):
    key = unique_key(40)
    assertions = [{"sign": s, "value": v, "confidence": 0.9} for s, v in key.items()]
    ap = _write(tmp_path, "a.json", assertions)
    kp = _write(tmp_path, "k.json", key)
    sha = hashlib.sha256(ap.read_bytes()).hexdigest()
    dp = _write(tmp_path, "d.json", {"method_commit": "abc", "control_id": "synthetic-1", "threshold": 0.5,
                                     "assertions_sha256": sha})
    log = tmp_path / "runs.jsonl"
    assert sc.main([str(ap), str(kp)]) == 2                                   # no declaration
    bad = _write(tmp_path, "bad.json", {"method_commit": "abc", "control_id": "synthetic-1", "threshold": 0.5,
                                        "assertions_sha256": "0" * 64})
    assert sc.main([str(ap), str(kp), "--declaration", str(bad), "--n-perm", "200"]) == 2   # sha mismatch
    r1 = sc.run(ap, kp, dp, log, n_perm=200)
    r2 = sc.run(ap, kp, dp, log, n_perm=200)
    assert r1["counts"] is True and r2["counts"] is False
    assert r1["inputs_sha256"]["assertions"] == sha
    assert len(log.read_text().strip().splitlines()) == 2


def test_inconclusive_band():
    # 5 correct of 5 unique-valued signs: the null is the fixed points of a random permutation, P = 1/120 = 0.0083,
    # within 3 SE of 0.01 at N = 10,000. The FDR bound fails at m = 5, so the verdict is still 'fail'.
    key = unique_key(50)
    r = sc.score([{"sign": s, "value": v} for s, v in list(key.items())[:5]], key, n_perm=10_000)
    assert r["p_inconclusive"] and sc.verdict(r) == "fail"
    near = dict(r, fdr_upper95=0.1)
    assert sc.verdict(near) == "inconclusive"
    assert sc.verdict(dict(near, p_inconclusive=False, p_value=0.001)) == "pass"


def test_deterministic_with_seed():
    key = synthetic_key()
    a = [{"sign": s, "value": "v1"} for s in list(key)[:30]]
    assert sc.score(a, key, n_perm=500, seed=3) == sc.score(a, key, n_perm=500, seed=3)
