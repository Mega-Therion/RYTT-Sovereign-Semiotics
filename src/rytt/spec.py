"""Canonical RYTT grammar specification loader and executable validator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SPEC_PATH = Path(__file__).with_name("data") / "rytt-spec-v0.1.0.json"
EXPECTED_SCHEMA = "rytt.sovereign-semiotics/1"
EXPECTED_VERSION = "0.1.0"


def load_spec() -> dict[str, Any]:
    """Load the versioned grammar that defines the RYTT vocabulary."""
    with SPEC_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _comparable(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only executable vocabulary fields; derived codepoints are checked separately."""
    fields = (
        "pua", "family", "vowel", "is_upper", "case_plane", "elevation_z",
        "trit_val", "sept_val", "path", "ops", "vectors", "meaning",
    )
    return {key: entry[key] for key in fields if key in entry}


def validate_against_canonical_spec(
    genome: Mapping[str, Mapping[str, Any]],
    ligatures: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Fail closed if executable compiler data differs from the canonical spec.

    The validator deliberately compares the complete semantic records, not only
    counts. This makes a vocabulary edit impossible to ship without updating the
    canonical artifact and its version.
    """
    spec = load_spec()
    if spec.get("schema") != EXPECTED_SCHEMA:
        raise RuntimeError(f"Unsupported RYTT spec schema: {spec.get('schema')!r}")
    if spec.get("version") != EXPECTED_VERSION:
        raise RuntimeError(f"Compiler expects RYTT spec {EXPECTED_VERSION}, got {spec.get('version')!r}")

    expected_genome = spec.get("genome", {})
    expected_ligatures = spec.get("ligatures", {})
    actual_genome = {key: _comparable(value) for key, value in genome.items()}
    actual_ligatures = {key: _comparable(value) for key, value in ligatures.items()}
    canonical_genome = {key: _comparable(value) for key, value in expected_genome.items()}
    canonical_ligatures = {key: _comparable(value) for key, value in expected_ligatures.items()}
    if actual_genome != canonical_genome:
        raise RuntimeError("RYTT genome differs from canonical specification")
    if actual_ligatures != canonical_ligatures:
        raise RuntimeError("RYTT ligatures differ from canonical specification")

    for kind, entries in (("genome", expected_genome), ("ligatures", expected_ligatures)):
        for key, entry in entries.items():
            pua = entry["pua"]
            expected_codepoint = entry["pua_codepoint"]
            actual_codepoint = f"0x{ord(pua):04X}"
            if actual_codepoint != expected_codepoint:
                raise RuntimeError(f"{kind} {key!r} has inconsistent pua_codepoint")
            if not (0xE000 <= ord(pua) <= 0xF8FF):
                raise RuntimeError(f"{kind} {key!r} is outside the Unicode Private Use Area")

    return spec
