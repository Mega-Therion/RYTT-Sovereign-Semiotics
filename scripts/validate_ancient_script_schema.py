#!/usr/bin/env python3
"""Validate every bundled ancient-script sample against the normative JSON Schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "research" / "ancient_scripts" / "schema" / "claim-record-v0.1.0.schema.json"
SAMPLES = [
    ROOT / "research" / "ancient_scripts" / "samples" / "cdli-proto-elamite-sample.json",
    ROOT / "research" / "ancient_scripts" / "samples" / "cdli-observation-sample.json",
]


def main() -> int:
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        checked = 0
        for sample in SAMPLES:
            payload = json.loads(sample.read_text(encoding="utf-8"))
            records = payload.get("records", [payload])
            for index, record in enumerate(records):
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
                if errors:
                    for error in errors:
                        path = "/".join(str(part) for part in error.path)
                        print(f"{sample.name}[{index}] {path}: {error.message}", file=sys.stderr)
                    return 1
                checked += 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to read schema/sample: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: Draft 2020-12 schema validates {checked} ancient-script sample records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
