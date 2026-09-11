#!/usr/bin/env python3
"""Generate the machine-readable RYTT canonical specification."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rytt.compiler import PUA_TO_PLAIN, RYTT_GENOME, RYTT_LIGATURES  # noqa: E402
from rytt import __version__  # noqa: E402

__spec_version__ = "0.1"


def build_spec() -> dict:
    primitives = []
    for key, value in RYTT_GENOME.items():
        primitives.append({
            "source": key,
            "codepoint": f"U+{ord(value['pua']):04X}",
            "codepoint_int": ord(value['pua']),
            "family": value["family"],
            "is_upper": value["is_upper"],
            "plane": "elevated" if value["case_plane"] == 1 else "ground",
            "elevation_z": value["elevation_z"],
            "trit": value.get("trit_val", 0),
            "sept": value.get("sept_val", 0),
        })
    chords = []
    for key, value in RYTT_LIGATURES.items():
        chords.append({
            "source": key,
            "codepoint": f"U+{ord(value['pua']):04X}",
            "codepoint_int": ord(value['pua']),
            "meaning": value.get("meaning", ""),
            "is_upper": value["is_upper"],
            "plane": "elevated" if value["case_plane"] == 1 else "ground",
            "elevation_z": value["elevation_z"],
        })
    return {
        "spec_version": __spec_version__,
        "package_version": __version__,
        "format": {
            "name": "RYTT token model",
            "display_serialization": "Unicode Private Use Area codepoints with U+00B7 for literal spaces",
            "matching": "greedy-longest-first; declaration order breaks equal-length ties",
            "passthrough": "unsupported alphabetic scripts and non-alphabetic characters survive unchanged",
            "round_trip": "decode(encode(source)) == source",
        },
        "planes": {
            "ground": {"case": "lowercase", "elevation_z": 0},
            "elevated": {"case": "uppercase", "elevation_z": 25},
        },
        "primitives": primitives,
        "chords": chords,
        "passthrough": {"pua_to_plain_count": len(PUA_TO_PLAIN)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "spec" / "vocabulary.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(build_spec(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            print(f"stale canonical spec: {target}")
            return 1
        print(f"canonical spec OK: {hashlib.sha256(content.encode()).hexdigest()[:16]}")
        return 0
    target.write_text(content, encoding="utf-8")
    print(f"generated {target.relative_to(ROOT)} sha256={hashlib.sha256(content.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
