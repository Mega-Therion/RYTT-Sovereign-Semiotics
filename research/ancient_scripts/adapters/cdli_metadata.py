"""Normalize CDLI artifact metadata into the RYTT research-record shape."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

CDLI_HOST = "https://cdli.earth"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        values = [_text(item) for item in value]
        joined = "; ".join(value for value in values if value)
        return joined or None
    if isinstance(value, dict):
        for key in (
            "value", "label", "name", "title", "fullform",
            "designation", "museum_number", "museum_no",
            "collection", "provenience", "period", "artifact_type",
            "material", "language", "id_text", "artifact_id", "id",
        ):
            candidate = _text(value.get(key))
            if candidate:
                return candidate
    return None


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _artifact_id(raw: dict[str, Any]) -> str:
    value = _text(raw.get("artifact_id") or raw.get("id_text") or raw.get("cdli_number") or raw.get("id"))
    if not value:
        raise ValueError("CDLI metadata requires artifact_id")
    if value.startswith("P"):
        numeric = value[1:]
    else:
        numeric = value
    if not numeric.isdigit():
        raise ValueError(f"CDLI artifact identifier must be numeric: {value!r}")
    if not 1 <= int(numeric) <= 999999:
        raise ValueError(f"CDLI artifact identifier is outside six-digit P range: {value!r}")
    return f"P{int(numeric):06d}"


def normalize_cdli_artifact(
    raw: dict[str, Any],
    *,
    script_name: str,
    retrieved_on: str,
) -> dict[str, Any]:
    """Return a schema-compatible RYTT record without inventing catalog values."""
    if not isinstance(raw, dict):
        raise TypeError("raw CDLI metadata must be an object")
    script_name = script_name.strip()
    if not script_name:
        raise ValueError("script_name is required")

    aid = _artifact_id(raw)
    period = _text(raw.get("period")) or _text(_nested(raw, "period", "period"))
    collection = _text(raw.get("collection"))
    if collection is None:
        collections = raw.get("collections")
        first_collection = _first(collections)
        collection = _text(first_collection)
        if collection is None:
            collection = _text(_nested(first_collection, "collection"))
    museum = _text(raw.get("museum_no") or raw.get("museum_number"))
    if museum is None:
        museum = _text(_nested(_first(raw.get("museum_numbers")), "museum_number"))

    provenience = _text(raw.get("provenience"))
    if provenience is None:
        provenience = _text(_first(raw.get("proveniences")))
    artifact_type = _text(raw.get("artifact_type"))
    if artifact_type is None:
        artifact_type = _text(_nested(raw, "artifact_type", "artifact_type"))
    material = _text(raw.get("material"))
    if material is None:
        material = _text(_nested(_first(raw.get("materials")), "material", "material"))

    language = _text(raw.get("language") or raw.get("languages"))
    return {
        "schema_version": "0.1.0",
        "record_status": "catalog_metadata_only",
        "artifact": {
            "artifact_id": f"CDLI:{aid}",
            "designation": _text(raw.get("designation")),
            "museum_number": museum,
            "collection": collection,
            "provenience": provenience,
            "period": period,
            "script": script_name,
            "language": language,
            "language_status": "undetermined" if language is None else "known",
            "object_type": artifact_type,
            "material": material,
            "source_url": f"{CDLI_HOST}/search?id={quote(aid)}&layout=compact",
        },
        "observations": [],
        "claims": [],
        "provenance": {
            "catalog_source": "Cuneiform Digital Library Initiative (CDLI)",
            "retrieved_on": retrieved_on,
            "metadata_rights_status": "review_required",
            "image_rights_status": "not_included",
            "notes": "Normalized catalog metadata only. Image assets are intentionally excluded; rights require separate review.",
        },
    }
