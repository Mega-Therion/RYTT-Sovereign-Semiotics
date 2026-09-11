#!/usr/bin/env python3
"""Compare the Rust portable core with the canonical Python benchmark corpus."""
from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"
TOLERANCE_PCT = 0.1


def main() -> int:
    namespace = runpy.run_path(str(ROOT / "benchmarks" / "run_benchmarks.py"))
    corpus = namespace["CORPUS"]
    reference_rows = {row["corpus"]: row for row in namespace["results"]}
    payload = [{"corpus": name, "source": source} for name, source in corpus.items()]

    process = subprocess.run(
        ["cargo", "run", "--quiet", "--bin", "rytt-core-benchmark"],
        cwd=ROOT / "crates" / "rytt-core",
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        print(process.stderr, file=sys.stderr)
        return process.returncode

    rust_rows = {row["corpus"]: row for row in json.loads(process.stdout)}
    comparisons = []
    failures = []
    for name in corpus:
        reference = reference_rows[name]
        rust = rust_rows[name]
        savings_delta = abs(reference["token_savings_pct"] - rust["token_savings_pct"])
        passed = (
            reference["source_chars"] == rust["source_characters"]
            and reference["token_count"] == rust["token_count"]
            and reference["round_trip_exact"] == rust["round_trip_exact"]
            and savings_delta <= TOLERANCE_PCT
        )
        comparison = {
            "corpus": name,
            "python_source_characters": reference["source_chars"],
            "rust_source_characters": rust["source_characters"],
            "python_token_count": reference["token_count"],
            "rust_token_count": rust["token_count"],
            "python_token_savings_pct": reference["token_savings_pct"],
            "rust_token_savings_pct": round(rust["token_savings_pct"], 2),
            "savings_delta_percentage_points": round(savings_delta, 4),
            "round_trip_exact": rust["round_trip_exact"],
            "passed": passed,
        }
        comparisons.append(comparison)
        if not passed:
            failures.append(name)

    RESULTS.mkdir(exist_ok=True)
    output_path = RESULTS / "rust_python_parity.json"
    output_path.write_text(json.dumps({
        "tolerance_percentage_points": TOLERANCE_PCT,
        "comparisons": comparisons,
    }, indent=2) + "\n")
    for row in comparisons:
        status = "PASS" if row["passed"] else "FAIL"
        print(
            f"{status} [{row['corpus']}] "
            f"python={row['python_token_count']} rust={row['rust_token_count']} "
            f"delta={row['savings_delta_percentage_points']:.4f} pp"
        )
    print(f"Parity report written to {output_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
