#!/usr/bin/env python3
"""Generate shared JSON conformance vectors from the reference compiler."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rytt import RyttCompiler  # noqa: E402

CASES = {
    "empty": "",
    "ascii_mixed_case": "Tyger Tyger, burning bright.",
    "chord_rich": "TION tion RYTT rytt transformation intentional",
    "whitespace": "line one\nline two\tline three",
    "symbols": "42% — [RYTT] {returns}!",
    "unicode_passthrough": "naïve café — 東京 — Δ",
    "all_ascii": "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ",
}


def build_vectors() -> list[dict]:
    compiler = RyttCompiler()
    vectors = []
    for name, source in CASES.items():
        result = compiler.compile(source)
        vectors.append({
            "id": name,
            "spec_version": "0.1",
            "source": source,
            "encoded_display": result.encoded_pua,
            "decoded": compiler.decompile(result.encoded_pua),
            "token_count": len(result.tokens),
            "tokens": [token.to_dict() for token in result.tokens],
        })
    return vectors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "conformance" / "vectors.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"format": "rytt-conformance", "version": "0.1", "vectors": build_vectors()}, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            print(f"stale conformance vectors: {target}")
            return 1
        print(f"conformance vectors OK sha256={hashlib.sha256(content.encode()).hexdigest()[:16]}")
        return 0
    target.write_text(content, encoding="utf-8")
    print(f"generated {target.relative_to(ROOT)} sha256={hashlib.sha256(content.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
