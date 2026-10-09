#!/usr/bin/env python3
"""Known-key calibration scorer (protocol: CALIBRATION_PROTOCOL_v0.1.1.md). Standard library only.

Usage:
  score_claims.py ASSERTIONS.json KEY.json --declaration DECL.json [--log RUNS.jsonl]
                  [--baseline BASELINE_ASSERTIONS.json] [--bands BANDS.json] [--n-perm N]
  ASSERTIONS.json: [{"sign": "...", "value": "...", "confidence": 0.8}, ...]
  KEY.json:        {"sign": "value" | ["value", "alternative", ...], ...}
  DECL.json:       {"method_commit", "control_id", "threshold", "assertions_sha256"}, committed before scoring
Exit: 0 gate pass · 1 gate fail · 2 bad input (incl. no scorable assertion) · 3 inconclusive (p within 3 SE of 0.01)

v0.1.1 changes, from the pre-run red team (2026-10-08):
- gate on the one-sided 95% Clopper-Pearson upper bound of the FDR, not the point estimate;
- permutation null among the ASSERTED signs only, signs sorted, so padding the key and key order can't move p;
- values normalized (NFC, casefold, trim), and the key may list accepted alternatives;
- a declaration file is required and checked against the assertions' sha256; every run is logged,
  and only the first run per (method_commit, control_id) counts;
- an optional frozen baseline (frequency-rank) must be beaten;
- booleans are rejected as confidences, and inputs are reported by sha256.
"""
import hashlib
import json
import math
import random
import sys
import time
import unicodedata

PROTOCOL = "known-key-calibration/0.1.1"
SEED = 20261008
N_PERM = 10_000
GATE_P = 0.01
GATE_FDR_UPPER = 0.20
CP_LEVEL = 0.95


class BadInput(ValueError):
    pass


def norm(v):
    return unicodedata.normalize("NFC", v).casefold().strip()


def _accepted(key_value):
    vals = key_value if isinstance(key_value, list) else [key_value]
    if not vals or not all(isinstance(x, str) for x in vals):
        raise BadInput(f"key values must be strings or non-empty lists of strings: {key_value!r}")
    return {norm(x) for x in vals}


def _validate(assertions):
    if not isinstance(assertions, list):
        raise BadInput("assertions must be a list")
    seen = set()
    for a in assertions:
        if not isinstance(a, dict) or not isinstance(a.get("sign"), str) or not isinstance(a.get("value"), str):
            raise BadInput(f"assertion must have string sign and value: {a!r}")
        c = a.get("confidence")
        if c is not None and (isinstance(c, bool) or not isinstance(c, (int, float)) or not 0 <= c <= 1):
            raise BadInput(f"confidence must be null or a number in [0, 1]: {a!r}")
        if a["sign"] in seen:
            raise BadInput(f"sign asserted more than once: {a['sign']!r}")
        seen.add(a["sign"])


def clopper_pearson_upper(k, n, level=CP_LEVEL):
    """One-sided upper confidence bound for a binomial proportion k/n."""
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    alpha = 1 - level

    def cdf(p):  # P(X <= k | n, p), in log space so large n cannot overflow
        lp, lq = math.log(p), math.log1p(-p)
        lc = math.lgamma(n + 1)
        return sum(math.exp(lc - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
                   for i in range(k + 1))

    for _ in range(200):  # bisection on P(X <= k | p) = alpha
        mid = (lo + hi) / 2
        if mid <= 0.0 or mid >= 1.0:
            break
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def score(assertions, key, threshold=0.0, n_perm=N_PERM, seed=SEED):
    """Score assertions with confidence >= threshold against a known key."""
    _validate(assertions)
    if not isinstance(key, dict) or not key:
        raise BadInput("key must be a non-empty object")
    accepted = {s: _accepted(v) for s, v in key.items()}
    kept = [a for a in assertions if (a.get("confidence") or 0.0) >= threshold] if threshold > 0 else list(assertions)
    pairs = sorted((a["sign"], norm(a["value"])) for a in kept if a["sign"] in accepted)
    unscorable = len(kept) - len(pairs)
    m = len(pairs)
    if m == 0:
        raise BadInput("no scorable assertion (sign IDs do not match the key)")
    hits = sum(1 for s, v in pairs if v in accepted[s])
    # null: re-pair the asserted signs with the key entries of the asserted signs, uniformly at random
    sets = [accepted[s] for s, _ in pairs]
    vals = [v for _, v in pairs]
    rng = random.Random(seed)
    idx = list(range(m))
    ge = 0
    null_sum = 0
    for _ in range(n_perm):
        rng.shuffle(idx)
        h = sum(1 for i in range(m) if vals[i] in sets[idx[i]])
        null_sum += h
        ge += h >= hits
    p = (1 + ge) / (n_perm + 1)
    se = math.sqrt(max(p * (1 - p), 1e-12) / n_perm)
    fdr = (m - hits) / m
    return {
        "protocol": PROTOCOL,
        "threshold": threshold,
        "m": m,
        "hits": hits,
        "unscorable": unscorable,
        "fdr": fdr,
        "fdr_upper95": clopper_pearson_upper(m - hits, m),
        "null_mean": null_sum / n_perm,
        "p_value": p,
        "p_se": se,
        "p_inconclusive": abs(p - GATE_P) < 3 * se,
        "n_perm": n_perm,
        "seed": seed,
    }


def gate(result, baseline=None):
    """Admissible only if p < GATE_P, the FDR upper bound <= GATE_FDR_UPPER, and (if given) the method's
    FDR upper bound is below the baseline's measured FDR on the same control."""
    ok = result["p_value"] < GATE_P and result["fdr_upper95"] <= GATE_FDR_UPPER
    if baseline is not None:
        ok = ok and result["fdr_upper95"] < baseline["fdr"]
    return ok


def verdict(result, baseline=None):
    """'fail' if any non-p criterion fails; else 'inconclusive' if p is within 3 SE of the gate; else pass/fail."""
    other_ok = result["fdr_upper95"] <= GATE_FDR_UPPER and (baseline is None or result["fdr_upper95"] < baseline["fdr"])
    if not other_ok:
        return "fail"
    if result["p_inconclusive"]:
        return "inconclusive"
    return "pass" if result["p_value"] < GATE_P else "fail"


def frequency_rank_baseline(sign_counts, value_counts):
    """Frozen baseline: pair signs and values by descending frequency rank (ties broken by name)."""
    signs = sorted(sign_counts, key=lambda s: (-sign_counts[s], s))
    values = sorted(value_counts, key=lambda v: (-value_counts[v], v))
    return [{"sign": s, "value": v, "confidence": 1.0} for s, v in zip(signs, values)]


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(assertions_path, key_path, decl_path, log_path=None, baseline_path=None, bands_path=None,
        n_perm=N_PERM, seed=SEED):
    decl = json.load(open(decl_path))
    for f in ("method_commit", "control_id", "threshold", "assertions_sha256"):
        if f not in decl:
            raise BadInput(f"declaration lacks {f!r}")
    a_sha = sha256_file(assertions_path)
    if decl["assertions_sha256"] != a_sha:
        raise BadInput("assertions file does not match the declaration's sha256")
    t = decl["threshold"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 1:
        raise BadInput("declared threshold must be a number in [0, 1]")
    assertions = json.load(open(assertions_path))
    key = json.load(open(key_path))
    r = score(assertions, key, t, n_perm, seed)
    base = None
    if baseline_path:
        base = score(json.load(open(baseline_path)), key, 0.0, n_perm, seed)
        r["baseline"] = {k: base[k] for k in ("m", "hits", "fdr", "fdr_upper95", "p_value")}
    r["gate_pass"] = gate(r, base)
    r["verdict"] = verdict(r, base)
    if bands_path:
        bands = json.load(open(bands_path))
        r["by_band"] = {}
        for b in sorted(set(bands.values())):
            sub = [a for a in assertions if bands.get(a["sign"]) == b]
            try:
                r["by_band"][b] = {k: v for k, v in score(sub, key, t, n_perm, seed).items()
                                   if k in ("m", "hits", "fdr", "fdr_upper95", "p_value")}
            except BadInput:
                r["by_band"][b] = {"m": 0}
    r["inputs_sha256"] = {"assertions": a_sha, "key": sha256_file(key_path), "declaration": sha256_file(decl_path)}
    r["declaration"] = {k: decl[k] for k in ("method_commit", "control_id", "threshold")}
    if log_path:
        prior = []
        try:
            prior = [json.loads(l) for l in open(log_path) if l.strip()]
        except FileNotFoundError:
            pass
        r["counts"] = not any(p.get("declaration", {}).get("method_commit") == decl["method_commit"]
                              and p.get("declaration", {}).get("control_id") == decl["control_id"] for p in prior)
        with open(log_path, "a") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **r}) + "\n")
    return r


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    try:
        if "--declaration" not in argv:
            raise BadInput("--declaration is required (CALIBRATION_PROTOCOL_v0.1.1.md, 'Declaration')")
        r = run(argv[0], argv[1], opt("--declaration"), opt("--log"), opt("--baseline"), opt("--bands"),
                int(opt("--n-perm", N_PERM)), int(opt("--seed", SEED)))
    except (BadInput, OSError, ValueError, KeyError, TypeError, IndexError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=2))
    return {"pass": 0, "fail": 1, "inconclusive": 3}[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
