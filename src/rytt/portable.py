"""Implementation-neutral JSON boundary for RYTT adapters."""
from __future__ import annotations

import json
from typing import Any

from .interchange import build_envelope, verify_envelope


def encode_request(payload: str | dict[str, Any]) -> dict[str, Any]:
    """Accept text or a JSON request and return a deterministic interchange envelope."""
    if isinstance(payload, str):
        source = payload
    else:
        if payload.get("operation", "encode") != "encode":
            raise ValueError("portable encode request requires operation=encode")
        source = payload.get("source_text")
        if not isinstance(source, str):
            raise ValueError("source_text must be a string")
    return build_envelope(source)


def decode_request(payload: str | dict[str, Any]) -> dict[str, Any]:
    """Decode an envelope or JSON string and return verification status plus text."""
    envelope = json.loads(payload) if isinstance(payload, str) else payload
    result = verify_envelope(envelope)
    result["decoded_text"] = envelope.get("verification", {}).get("decoded_text")
    return result
