#!/usr/bin/env python3
"""Check canonical PUA boundaries against the standalone formal core contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "spec" / "vocabulary.json").read_text(encoding="utf-8"))
primitive_ground = sorted(item["codepoint_int"] for item in spec["primitives"] if item["plane"] == "ground")
primitive_elevated = sorted(item["codepoint_int"] for item in spec["primitives"] if item["plane"] == "elevated")
chords = sorted(item["codepoint_int"] for item in spec["chords"])
assert (min(primitive_ground), max(primitive_ground)) == (0xE000, 0xE019)
assert (min(primitive_elevated), max(primitive_elevated)) == (0xE800, 0xE819)
assert min(value for value in chords if value < 0xE800) == 0xE020
assert min(value for value in chords if value >= 0xE800) == 0xE820
print("formal boundary alignment OK: ground E000/E020, elevated E800/E820")
