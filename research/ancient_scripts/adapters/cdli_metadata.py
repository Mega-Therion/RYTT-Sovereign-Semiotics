"""Normalize CDLI artifact metadata into the RYTT research-record shape."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        parts = [_text(item) for item in value]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("label", "name", "title", "value", "fullform"):
            candidate = _text(value.get(key))
            if candidate:
                return candidate
    return str(value).strip() or None


def _artifact_id(raw: dict[str, Any]) -> str:
    value = _text(raw.get("artifact_id") or raw.get("id") or raw.get("cdli_number"))
    if not value:
        raise ValueError("CDLI metadata requires artifact_id")
    return value if value.startswith("P") else f"P{value}"


def normalize_cdli_artifact(raw: dict[str, Any], *, retrieved_on: str) -> dict[str, Any]:
    """Return a schema-compatible RYTT record from flat CDLI metadata fields."""
    if not isinstance(raw, dict):
        raise TypeError("raw CDLI metadata must be an object")
    aid = _artifact_id(raw)
    source_url = f"https://cdli.earth/search?id={quote(aid)}&layout=compact"
    period = _text(raw.get("period"))
    collection = _text(raw.get("collections") or raw.get("collection"))
    if not period or not collection:
        raise ValueError("CDLI metadata requires period and collections")
    return {
        "schema_version": "0.1.0",
        "record_status": "catalog_metadata_only",
        "artifact": {
            "artifact_id": f"CDLI:{aid}",
            "designation": _text(raw.get("designation")),
            "museum_number": _text(raw.get("museum_no") or raw.get("museum_number")),
            "collection": collection,
            "provenience": _text(raw.get("provenience")),
            "period": period,
            "object_type": _text(raw.get("artifact_type") or raw.get("object_type")),
            "material": _text(raw.get("materials") or raw.get("material")),
            "source_url": source_url,
        },
        "observations": [],
        "claims": [],
        "provenance": {
            "catalog_source": "Cuneiform Digital Library Initiative (CDLI)",
            "retrieved_on": retrieved_on,
            "metadata_rights_status": "review_required",
            "image_rights_status": "not_included",
            "notes": "Normalized catalog metadata only. Image assets are intentionally excluded; rights require separate review before reuse.",
        },
    }
