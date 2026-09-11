#!/usr/bin/env python3
"""Replay every shared conformance vector against the Python reference compiler."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rytt import RyttCompiler  # noqa: E402


def main() -> int:
    payload = json.loads((ROOT / "conformance" / "vectors.json").read_text(encoding="utf-8"))
    compiler = RyttCompiler()
    failures = []
    for vector in payload["vectors"]:
        result = compiler.compile(vector["source"])
        decoded = compiler.decompile(result.encoded_pua)
        if decoded != vector["decoded"] or decoded != vector["source"] or result.encoded_pua != vector["encoded_display"]:
            failures.append(vector["id"])
    if failures:
        print(f"conformance failures: {', '.join(failures)}")
        return 1
    print(f"verified {len(payload['vectors'])} vectors for spec {payload['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
