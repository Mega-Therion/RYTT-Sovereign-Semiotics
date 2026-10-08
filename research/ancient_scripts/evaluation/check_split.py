"""Check that artifact-level evaluation splits contain no duplicate or cross-split artifacts."""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED = {"train", "validation", "test"}


def validate_split_manifest(document: dict) -> None:
    if not isinstance(document, dict) or document.get("version") != "0.1.0":
        raise ValueError("split manifest version must be 0.1.0")
    assignments = document.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise ValueError("assignments must be a non-empty array")

    seen: dict[str, str] = {}
    for i, item in enumerate(assignments):
        if not isinstance(item, dict):
            raise ValueError(f"assignments[{i}] must be an object")
        artifact_id = item.get("artifact_id")
        split = item.get("split")
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            raise ValueError(f"assignments[{i}].artifact_id is required")
        if split not in ALLOWED:
            raise ValueError(f"assignments[{i}].split is invalid")
        if artifact_id in seen:
            raise ValueError(f"artifact appears more than once: {artifact_id}")
        seen[artifact_id] = split


def main() -> int:
    path = Path(__file__).with_name("splits").joinpath("pilot-split-v0.1.0.json")
    try:
        validate_split_manifest(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: artifact-level pilot split contains unique assignments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
