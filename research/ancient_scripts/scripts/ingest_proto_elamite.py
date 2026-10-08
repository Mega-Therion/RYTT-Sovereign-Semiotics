#!/usr/bin/env python3
"""Fetch and freeze a rights-aware Proto-Elamite CDLI metadata snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

HOST = "https://cdli.earth"
SCRIPT = "Proto-Elamite"
PERIOD = "Proto-Elamite"
PAGE_SIZE = 1000
MIN_EXPECTED_COUNT = 1700
USER_AGENT = "RYTT-AncientScript-Ingest/0.2.0"
NEXT_LINK_RE = re.compile(r'<([^>]+)>\s*;\s*rel=["\']?next["\']?', re.I)
RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class IngestionError(RuntimeError):
    pass


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        values = [_text(item) for item in value]
        joined = "; ".join(v for v in values if v)
        return joined or None
    if isinstance(value, dict):
        for key in (
            "value", "label", "name", "title", "fullform",
            "artifact_id", "id_text", "id",
            "designation", "museum_number", "museum_no",
            "collection", "provenience", "period", "artifact_type",
            "material", "language",
        ):
            candidate = _text(value.get(key))
            if candidate:
                return candidate
    return None


def _first_nested(value: Any, *paths: tuple[Any, ...]) -> Any:
    for path in paths:
        current = value
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def _artifact_id(raw: dict[str, Any]) -> str:
    value = _text(raw.get("id_text") or raw.get("artifact_id") or raw.get("cdli_number") or raw.get("id"))
    if not value:
        raise IngestionError("artifact has no CDLI identifier")
    if not value.startswith("P"):
        value = f"P{value}"
    if not re.fullmatch(r"P\d{6}", value):
        raise IngestionError(f"invalid CDLI artifact identifier: {value!r}")
    return value


def normalize_record(raw: dict[str, Any], *, retrieved_on: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IngestionError("search result is not an object")
    aid = _artifact_id(raw)

    collection_raw = (
        raw.get("collection")
        or raw.get("collections")
        or _first_nested(raw, ("collections", 0, "collection", "collection"))
    )
    museum_raw = (
        raw.get("museum_no")
        or raw.get("museum_number")
        or _first_nested(raw, ("museum_numbers", 0, "museum_number"))
    )
    provenience_raw = raw.get("provenience")
    if isinstance(provenience_raw, list):
        provenience_raw = provenience_raw[0] if provenience_raw else None
    period_raw = raw.get("period")
    if isinstance(period_raw, dict):
        period_raw = period_raw.get("period")
    artifact_type_raw = raw.get("artifact_type")
    if isinstance(artifact_type_raw, dict):
        artifact_type_raw = artifact_type_raw.get("artifact_type")
    material_raw = raw.get("material") or raw.get("materials")
    if isinstance(material_raw, list):
        material_raw = material_raw[0] if material_raw else None

    period = _text(period_raw)
    if period and PERIOD.lower() not in period.lower():
        raise IngestionError(f"{aid}: returned period is not Proto-Elamite: {period!r}")

    return {
        "schema_version": "0.1.0",
        "record_status": "catalog_metadata_only",
        "artifact": {
            "artifact_id": f"CDLI:{aid}",
            "designation": _text(raw.get("designation")),
            "museum_number": _text(museum_raw),
            "collection": _text(collection_raw),
            "provenience": _text(provenience_raw),
            "period": period,
            "script": SCRIPT,
            "language": _text(raw.get("language") or raw.get("languages")),
            "language_status": "undetermined" if not _text(raw.get("language") or raw.get("languages")) else "known",
            "object_type": _text(artifact_type_raw),
            "material": _text(material_raw),
            "source_url": f"{HOST}/search?id={urllib.parse.quote(aid)}&layout=compact",
        },
        "observations": [],
        "claims": [],
        "provenance": {
            "catalog_source": "Cuneiform Digital Library Initiative (CDLI)",
            "retrieved_on": retrieved_on,
            "metadata_rights_status": "review_required",
            "image_rights_status": "not_included",
            "notes": "Normalized catalog metadata only. No image assets or image-derived data are included.",
        },
    }


def parse_payload(payload: bytes) -> list[dict[str, Any]]:
    text = payload.decode("utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(stripped.splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestionError(f"invalid NDJSON at line {line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise IngestionError(f"NDJSON line {line_no} is not an object")
            records.append(value)
        return records
    if isinstance(parsed, list):
        if not all(isinstance(item, dict) for item in parsed):
            raise IngestionError("JSON search response contains a non-object record")
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    raise IngestionError("search response is neither NDJSON nor JSON objects")


def _next_url(headers: Any, base: str) -> str | None:
    for link in headers.get_all("Link") or []:
        match = NEXT_LINK_RE.search(link)
        if match:
            return urllib.parse.urljoin(base.rstrip("/") + "/", match.group(1))
    return None


def fetch_url(url: str, *, timeout: float, retries: int) -> tuple[bytes, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/x-ndjson, application/json;q=0.9",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt >= retries:
                raise IngestionError(f"CDLI request failed with HTTP {exc.code}: {url}") from exc
            time.sleep(min(30.0, 2.0 ** attempt))
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= retries:
                raise IngestionError(f"CDLI request failed after {retries + 1} attempts: {url}: {exc}") from exc
            time.sleep(min(30.0, 2.0 ** attempt))
    raise AssertionError("unreachable")


def canonical_records_hash(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    temp.replace(path)


def ingest(*, host: str, output: Path, manifest: Path, min_count: int, timeout: float, retries: int) -> tuple[int, str]:
    base = host.rstrip("/")
    query = urllib.parse.urlencode([("limit", str(PAGE_SIZE)), ("f[period][]", PERIOD)])
    url = f"{base}/search?{query}"
    retrieved_on = datetime.now(timezone.utc).date().isoformat()
    records: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    page = 0

    while url:
        if url in seen_urls:
            raise IngestionError(f"pagination loop detected at {url}")
        seen_urls.add(url)
        page += 1
        payload, headers = fetch_url(url, timeout=timeout, retries=retries)
        page_records = parse_payload(payload)
        if not page_records:
            raise IngestionError(f"CDLI returned an empty page: page {page}")
        if len(page_records) > PAGE_SIZE:
            raise IngestionError(f"CDLI returned more than {PAGE_SIZE} records on page {page}")
        for raw in page_records:
            record = normalize_record(raw, retrieved_on=retrieved_on)
            aid = record["artifact"]["artifact_id"]
            if aid in seen_ids:
                raise IngestionError(f"duplicate artifact across pages: {aid}")
            seen_ids.add(aid)
            records.append(record)

        next_url = _next_url(headers, base)
        if next_url is None and len(page_records) == PAGE_SIZE:
            raise IngestionError("page ended at the request limit without a next-page link")
        url = next_url

    if len(records) < min_count:
        raise IngestionError(f"only {len(records)} records ingested; minimum expected is {min_count}")

    records.sort(key=lambda record: record["artifact"]["artifact_id"])
    digest = canonical_records_hash(records)
    artifact_ids_digest = hashlib.sha256(
        "\n".join(record["artifact"]["artifact_id"] for record in records).encode("utf-8")
    ).hexdigest()
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    corpus = {
        "dataset_version": "0.2.0",
        "dataset_status": "frozen_metadata_snapshot",
        "corpus": {
            "name": "CDLI Proto-Elamite",
            "script": SCRIPT,
            "period_filter": PERIOD,
            "artifact_count": len(records),
            "source": f"{base}/search",
            "source_query": query,
            "retrieved_on_utc": captured_at,
        },
        "rights": {
            "metadata_rights_status": "review_required",
            "images_included": False,
            "image_rights_status": "not_included",
        },
        "snapshot_sha256": digest,
        "records": records,
    }
    manifest_payload = {
        "manifest_version": "0.2.0",
        "status": "frozen_metadata_snapshot",
        "corpus": corpus["corpus"],
        "snapshot_sha256": digest,
        "artifact_ids_sha256": artifact_ids_digest,
        "rights": corpus["rights"],
        "evaluation": {
            "status": "not_ready",
            "reason": "Labels, preprocessing, artifact-level held-out splits, and baseline replication have not yet been frozen.",
        },
        "source_policy": {
            "api_documented": True,
            "image_assets_included": False,
            "metadata_license_status": "review_required",
        },
    }

    atomic_write_json(output, corpus)
    atomic_write_json(manifest, manifest_payload)
    return len(records), digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--output", type=Path, default=Path("research/ancient_scripts/snapshots/cdli-proto-elamite-corpus.json"))
    parser.add_argument("--manifest", type=Path, default=Path("research/ancient_scripts/snapshots/cdli-proto-elamite-manifest.json"))
    parser.add_argument("--min-count", type=int, default=MIN_EXPECTED_COUNT)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_count < 1:
        print("--min-count must be positive", file=sys.stderr)
        return 2
    try:
        count, digest = ingest(
            host=args.host,
            output=args.output,
            manifest=args.manifest,
            min_count=args.min_count,
            timeout=args.timeout,
            retries=args.retries,
        )
    except (IngestionError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: froze {count} Proto-Elamite metadata records; snapshot_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
