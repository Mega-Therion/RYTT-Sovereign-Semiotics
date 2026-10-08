#!/usr/bin/env python3
"""Known-key calibration scorer (protocol: CALIBRATION_PROTOCOL_v0.1.0.md). Standard library only.

Usage: score_claims.py ASSERTIONS.json KEY.json [--threshold T] [--n-perm N] [--seed S]
  ASSERTIONS.json: [{"sign": "...", "value": "...", "confidence": 0.8}, ...]
  KEY.json:        {"sign": "value", ...}
Prints a JSON report; exit 0 if the gate passes at the threshold, 1 if it fails, 2 on bad input.
"""
import json
import random
import sys

PROTOCOL = "known-key-calibration/0.1.0"
SEED = 20261008
N_PERM = 10_000
THRESHOLDS = (0.5, 0.7, 0.9)
GATE_P = 0.01
GATE_FDR = 0.20


def _validate(assertions):
    seen = set()
    for a in assertions:
        if not isinstance(a, dict) or not isinstance(a.get("sign"), str) or not isinstance(a.get("value"), str):
            raise ValueError(f"assertion must have string sign and value: {a!r}")
        c = a.get("confidence")
        if c is not None and not (isinstance(c, (int, float)) and 0 <= c <= 1):
            raise ValueError(f"confidence must be null or in [0, 1]: {a!r}")
        if a["sign"] in seen:
            raise ValueError(f"sign asserted more than once: {a['sign']!r}")
        seen.add(a["sign"])


def _hits(pairs, key):
    return sum(1 for s, v in pairs if key[s] == v)


def score(assertions, key, threshold=0.0, n_perm=N_PERM, seed=SEED):
    """Score assertions with confidence >= threshold against a known key."""
    _validate(assertions)
    if not key:
        raise ValueError("empty key")
    kept = [a for a in assertions if (a.get("confidence") or 0.0) >= threshold] if threshold > 0 else list(assertions)
    pairs = [(a["sign"], a["value"]) for a in kept if a["sign"] in key]
    unscorable = len(kept) - len(pairs)
    m = len(pairs)
    hits = _hits(pairs, key)
    signs = list(key)
    values = [key[s] for s in signs]
    rng = random.Random(seed)
    null = []
    for _ in range(n_perm):
        rng.shuffle(values)
        null.append(_hits(pairs, dict(zip(signs, values))))
    null.sort()
    ge = sum(1 for h in null if h >= hits)
    return {
        "protocol": PROTOCOL,
        "threshold": threshold,
        "m": m,
        "hits": hits,
        "unscorable": unscorable,
        "fdr": (m - hits) / m if m else None,
        "null_mean": sum(null) / n_perm,
        "null_q95": null[min(n_perm - 1, int(0.95 * n_perm))],
        "p_value": (1 + ge) / (n_perm + 1),
        "n_perm": n_perm,
        "seed": seed,
    }


def gate(result):
    """Admissible for Proto-Elamite scoring only if p < GATE_P and measured FDR <= GATE_FDR."""
    return result["m"] > 0 and result["p_value"] < GATE_P and result["fdr"] <= GATE_FDR


def report(assertions, key, threshold, n_perm=N_PERM, seed=SEED):
    main = score(assertions, key, threshold, n_perm, seed)
    main["gate_pass"] = gate(main)
    main["by_threshold"] = {str(t): score(assertions, key, t, n_perm, seed) for t in THRESHOLDS}
    return main


def main(argv):
    try:
        assertions = json.load(open(argv[0]))
        key = json.load(open(argv[1]))
        t = float(argv[argv.index("--threshold") + 1]) if "--threshold" in argv else 0.0
        n = int(argv[argv.index("--n-perm") + 1]) if "--n-perm" in argv else N_PERM
        s = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else SEED
        r = report(assertions, key, t, n, s)
    except (OSError, ValueError, IndexError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=2))
    return 0 if r["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
