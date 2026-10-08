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

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from research.ancient_scripts.adapters.cdli_metadata import normalize_cdli_artifact

HOST = "https://cdli.earth"
SCRIPT = "Proto-Elamite"
PERIOD = "Proto-Elamite"
PAGE_SIZE = 1000
MIN_EXPECTED_COUNT = 1700
USER_AGENT = "RYTT-AncientScript-Ingest/0.2.0"
NEXT_LINK_RE = re.compile(r'<([^>]+)>\s*;\s*rel=["\']?next["\']?', re.I)
ACCEPTED_TYPES = {"application/x-ndjson", "application/json"}
RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class IngestionError(RuntimeError):
    """Raised when an ingestion cannot produce a complete, trustworthy snapshot."""


def parse_payload(payload: bytes) -> list[dict]:
    text = payload.decode("utf-8")
    stripped = text.strip()
    if not stripped:
        return []

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        records = []
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


def next_url(headers, base: str, current_page: int, page_size: int, current_count: int) -> str | None:
    links = headers.get_all("Link") or []
    if not links:
        raw_link = headers.get("Link") if hasattr(headers, "get") else None
        if raw_link:
            links = [raw_link]
    for link in links:
        for match in NEXT_LINK_RE.finditer(link):
            return urllib.parse.urljoin(base.rstrip("/") + "/", match.group(1))

    # Current CDLI responses have been observed to emit a "first&page=1" link
    # while omitting "next" when a page is exactly full. The explicit page cursor
    # supplied by CDLI is the only fallback we use; no result-offset is invented.
    if current_count == page_size:
        first_link = next((link for link in links if 'rel="first"' in link), None)
        first_match = re.search(r'<([^>]+)>\s*;\s*rel="first"', first_link, re.I) if first_link else None
        if first_match:
            parsed = urllib.parse.urlsplit(urllib.parse.urljoin(base.rstrip("/") + "/", first_match.group(1)))
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            if "page" in params:
                params["page"] = [str(current_page + 1)]
                query = urllib.parse.urlencode(params, doseq=True)
                return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))
    return None


def fetch_url(url: str, *, timeout: float, retries: int) -> tuple[bytes, object]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/x-ndjson, application/json;q=0.9", "User-Agent": USER_AGENT},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type not in ACCEPTED_TYPES:
                    raise IngestionError(f"unexpected CDLI content type {content_type!r} for {url}")
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


def canonical_records_hash(records: list[dict]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def artifact_ids_hash(records: list[dict]) -> str:
    return hashlib.sha256(
        "\n".join(record["artifact"]["artifact_id"] for record in records).encode("utf-8")
    ).hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    temp.replace(path)


def ingest(
    *,
    host: str,
    output: Path,
    manifest: Path,
    min_count: int,
    timeout: float,
    retries: int,
) -> tuple[int, str]:
    base = host.rstrip("/")
    query = urllib.parse.urlencode([("limit", str(PAGE_SIZE)), ("simple-field[]", "period"), ("simple-value[]", PERIOD), ("simple-op[]", "AND")])
    url = f"{base}/search?{query}"
    retrieval_day = datetime.now(timezone.utc).date().isoformat()
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    records: list[dict] = []
    page = 0

    while url:
        if url in seen_urls:
            raise IngestionError(f"pagination loop detected at {url}")
        seen_urls.add(url)
        page += 1

        payload, headers = fetch_url(url, timeout=timeout, retries=retries)
        page_records = parse_payload(payload)
        if not page_records:
            raise IngestionError(f"CDLI returned an empty page: {page}")
        if len(page_records) > PAGE_SIZE:
            raise IngestionError(f"CDLI returned {len(page_records)} records on page {page}; limit is {PAGE_SIZE}")

        for raw in page_records:
            record = normalize_cdli_artifact(raw, script_name=SCRIPT, retrieved_on=retrieval_day)
            aid = record["artifact"]["artifact_id"]
            period = record["artifact"]["period"]
            if period is None:
                raise IngestionError(f"{aid}: filtered API result has no period value to verify")
            if PERIOD.lower() not in period.lower():
                raise IngestionError(f"{aid}: returned period is not Proto-Elamite: {period!r}")
            if aid in seen_ids:
                raise IngestionError(f"duplicate artifact across pages: {aid}")
            seen_ids.add(aid)
            records.append(record)

        url = next_url(headers, base, page, PAGE_SIZE, len(page_records))
        if url is None and len(page_records) == PAGE_SIZE:
            get_header = headers.get if hasattr(headers, "get") else lambda _key: None
            diagnostics = {
                key: get_header(key)
                for key in ("Link", "Content-Range", "Content-Location", "X-Total-Count", "X-Total", "X-Page", "X-Next-Page")
                if get_header(key)
            }
            raise IngestionError(f"page ended at the request limit without a next-page link; headers={diagnostics}")

    if len(records) < min_count:
        raise IngestionError(f"only {len(records)} records ingested; minimum expected is {min_count}")

    records.sort(key=lambda record: record["artifact"]["artifact_id"])
    digest = canonical_records_hash(records)
    ids_digest = artifact_ids_hash(records)
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    corpus_metadata = {
        "name": "CDLI Proto-Elamite",
        "script": SCRIPT,
        "period_filter": PERIOD,
        "artifact_count": len(records),
        "source": f"{base}/search",
        "source_query": query,
        "retrieved_on_utc": captured_at,
        "canonicalization": "JSON UTF-8 sort_keys=true separators=(',', ':') over sorted records",
    }
    rights = {
        "metadata_rights_status": "review_required",
        "images_included": False,
        "image_rights_status": "not_included",
    }

    corpus = {
        "dataset_version": "0.2.0",
        "dataset_status": "frozen_metadata_snapshot",
        "corpus": corpus_metadata,
        "rights": rights,
        "snapshot_sha256": digest,
        "records": records,
    }
    manifest_payload = {
        "manifest_version": "0.2.0",
        "status": "frozen_metadata_snapshot",
        "corpus": corpus_metadata,
        "snapshot_sha256": digest,
        "artifact_ids_sha256": ids_digest,
        "rights": rights,
        "evaluation": {
            "status": "not_ready",
            "reason": "Labels, preprocessing, artifact-level held-out splits, and baseline replication remain separate frozen stages.",
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
    parser = argparse.ArgumentParser(description=__doc__)
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
