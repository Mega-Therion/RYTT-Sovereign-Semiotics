#!/usr/bin/env python3
"""
RYTT Benchmark Suite v0.1.0
Runs 7 corpus categories, outputs JSON results to benchmarks/results/.
"""
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rytt.compiler import RyttCompiler

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CORPUS = {
    "prose": (
        "The quick brown fox jumps over the lazy dog. "
        "Sovereign intelligence requires both formal structure and semantic depth. "
        "All things return to their origin through the RYTT invariant."
    ),
    "code": (
        "def encode(text: str) -> str:\n"
        "    return compiler.compile(text).encoded_pua\n\n"
        "for token in result.tokens:\n"
        "    print(token.to_dict())\n"
    ),
    "mixed_casing": "RYTT The Quick Brown Fox JUMPS over THE lazy DOG",
    "punctuation": (
        "...wait\u2014what?! (yes, really.) \"Hello,\" said the fox. "
        "Score: 100% \u2014 a perfect round-trip."
    ),
    "whitespace": (
        "  leading   spaces   and   trailing  \n"
        "\ttabs\t and\nnewlines\n"
        "  preserved   exactly  "
    ),
    "unicode_passthrough": (
        "\u03b1 \u03b2 \u03b3 \u2192 \u221e \u2295 \u2207 "
        "\u00e9 \u00f1 \u00fc \u4e2d\u6587 \u65e5\u672c\u8a9e"
    ),
    "ligature_rich": (
        "RYTT TION MENT ING STR THE AND NOT FOR CON PRO "
        "rytt tion ment ing str the and not for con pro "
        "TH ST IN ER ON AT RY TT RE EE"
    ),
}

compiler = RyttCompiler()

results = []
all_passed = True

for name, text in CORPUS.items():
    t0 = time.perf_counter()
    result = compiler.compile(text)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000

    decoded = compiler.decompile(result.encoded_pua)
    exact = decoded == text
    if not exact:
        all_passed = False
        print(f"FAIL [{name}]: round-trip mismatch", file=sys.stderr)

    chord_count = sum(1 for t in result.tokens if t.is_chord)
    entry = {
        "corpus": name,
        "source_chars": len(text),
        "token_count": len(result.tokens),
        "chord_count": chord_count,
        "utf8_bytes_source": len(text.encode()),
        "utf8_bytes_encoded": len(result.encoded_pua.encode()),
        "compression_ratio": round(result.compression_ratio, 4),
        "token_savings_pct": round(result.token_savings_pct, 2),
        "runtime_us": round(elapsed_us, 2),
        "parity_mod24": result.parity_mod24,
        "round_trip_exact": exact,
    }
    results.append(entry)
    status = "PASS" if exact else "FAIL"
    print(f"{status} [{name}] {len(text)}ch "
          f"{len(result.tokens)}tok "
          f"{chord_count}chords "
          f"ratio={entry['compression_ratio']} "
          f"{elapsed_us:.0f}\u03bcs")

outpath = RESULTS_DIR / "benchmark_results.json"
outpath.write_text(json.dumps({"version": "0.1.0", "results": results}, indent=2))
print(f"\nResults written to {outpath}")

if not all_passed:
    print("\nSome corpora FAILED round-trip.", file=sys.stderr)
    sys.exit(1)
print(f"\nAll {len(results)} corpora passed round-trip.")
