#!/usr/bin/env python3
"""Small deterministic performance smoke test, not a comparative benchmark."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rytt import RyttCompiler  # noqa: E402

text = ("RYTT TION MENT — reversible exact text. " * 2000).strip()
compiler = RyttCompiler()
start = time.perf_counter()
result = compiler.compile(text)
elapsed_ms = (time.perf_counter() - start) * 1000
assert compiler.decompile(result.encoded_pua) == text
payload = {"source_chars": len(text), "tokens": len(result.tokens), "elapsed_ms": round(elapsed_ms, 3), "round_trip_exact": True}
print(json.dumps(payload, indent=2))
