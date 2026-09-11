"""Versioned RYTT interchange and verified artifact export."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from .compiler import RyttCompiler

FORMAT_VERSION = "0.1"
SPEC_VERSION = "0.1"
ROOT = Path(__file__).resolve().parents[2]


def vocabulary_hash() -> str:
    path = ROOT / "spec" / "vocabulary.json"
    if not path.exists():
        return "unavailable"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_envelope(source_text: str, compiler: RyttCompiler | None = None) -> dict[str, Any]:
    compiler = compiler or RyttCompiler()
    result = compiler.compile(source_text)
    decoded = compiler.decompile(result.encoded_pua)
    return {
        "format": "rytt",
        "format_version": FORMAT_VERSION,
        "spec_version": SPEC_VERSION,
        "vocabulary_sha256": vocabulary_hash(),
        "source_encoding": "utf-8",
        "source_text": source_text,
        "encoded_display": result.encoded_pua,
        "tokens": [
            {
                "index": index,
                "source": token.raw,
                "kind": "chord" if token.is_chord else ("glyph" if token.case_plane >= 0 else "passthrough"),
                "plane": "elevated" if token.case_plane == 1 else ("ground" if token.case_plane == 0 else None),
                "codepoint": f"U+{ord(token.pua):04X}" if len(token.pua) == 1 and ord(token.pua) >= 0xE000 else None,
                "codepoint_int": ord(token.pua) if len(token.pua) == 1 and ord(token.pua) >= 0xE000 else None,
                "is_chord": token.is_chord,
                "passthrough": token.case_plane < 0,
            }
            for index, token in enumerate(result.tokens)
        ],
        "metrics": {
            "source_characters": len(source_text),
            "rytt_tokens": len(result.tokens),
            "source_utf8_bytes": len(source_text.encode("utf-8")),
            "encoded_utf8_bytes": len(result.encoded_pua.encode("utf-8")),
            "chord_tokens": sum(token.is_chord for token in result.tokens),
            "character_reduction_pct": round((1 - len(result.tokens) / max(1, len(source_text))) * 100, 2),
        },
        "verification": {"round_trip_exact": decoded == source_text, "decoded_text": decoded},
    }


def verify_envelope(envelope: dict[str, Any], compiler: RyttCompiler | None = None) -> dict[str, Any]:
    compiler = compiler or RyttCompiler()
    errors: list[str] = []
    if envelope.get("format") != "rytt": errors.append("unsupported format")
    if envelope.get("format_version") != FORMAT_VERSION: errors.append("unsupported format version")
    if envelope.get("spec_version") != SPEC_VERSION: errors.append("unsupported specification version")
    if envelope.get("vocabulary_sha256") not in {vocabulary_hash(), "unavailable"}: errors.append("vocabulary hash mismatch")
    source = envelope.get("source_text")
    encoded = envelope.get("encoded_display")
    if not isinstance(source, str) or not isinstance(encoded, str): errors.append("source_text and encoded_display are required")
    else:
        decoded = compiler.decompile(encoded)
        if decoded != source: errors.append("decoded text does not match source_text")
        if envelope.get("verification", {}).get("round_trip_exact") is not True: errors.append("verification flag is not exact")
    return {"valid": not errors, "errors": errors, "vocabulary_sha256": vocabulary_hash()}


def export_bundle(source_text: str, output: str | Path, compiler: RyttCompiler | None = None) -> Path:
    envelope = build_envelope(source_text, compiler)
    output_path = Path(output)
    if output_path.suffix.lower() != ".zip": output_path = output_path.with_suffix(".zip")
    readme = "# RYTT verified artifact\n\nReplay with `rytt artifact-verify bundle.zip`.\n"
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("artifact.json", json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("source.txt", source_text)
        archive.writestr("encoded.rytt", envelope["encoded_display"])
        archive.writestr("trace.json", json.dumps(envelope["tokens"], ensure_ascii=False, indent=2) + "\n")
        archive.writestr("metrics.json", json.dumps(envelope["metrics"], indent=2) + "\n")
        archive.writestr("verification.json", json.dumps(envelope["verification"], indent=2) + "\n")
        archive.writestr("README.md", readme)
    return output_path


def verify_bundle(bundle: str | Path) -> dict[str, Any]:
    with zipfile.ZipFile(bundle) as archive:
        envelope = json.loads(archive.read("artifact.json"))
    return verify_envelope(envelope)
