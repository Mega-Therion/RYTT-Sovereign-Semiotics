import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.ancient_scripts.scripts import ingest_proto_elamite as ingest


class FakeHeaders:
    def __init__(self, links=None):
        self.links = links or []

    def get_all(self, name):
        return self.links if name.lower() == "link" else []


def raw_record(aid):
    return {
        "id_text": aid,
        "period": {"period": "Proto-Elamite (ca. 3100-2900 BC)"},
        "collections": [{"collection": {"collection": "Louvre Museum, Paris, France"}}],
        "provenience": {"provenience": "Susa (mod. Shush)"},
        "artifact_type": {"artifact_type": "tablet"},
        "materials": [{"material": {"material": "clay"}}],
    }


class ProtoElamiteIngestionTests(unittest.TestCase):
    def test_ndjson_parser_accepts_multiple_objects(self):
        payload = b'{"id_text":"P008001"}\n{"id_text":"P008002"}\n'
        records = ingest.parse_payload(payload)
        self.assertEqual([item["id_text"] for item in records], ["P008001", "P008002"])

    def test_pagination_is_followed_and_records_are_sorted(self):
        pages = [
            (b'{"id_text":"P008002","period":{"period":"Proto-Elamite"}}\n',
             FakeHeaders(['<https://cdli.earth/search?cursor=2>; rel="next"'])),
            (b'{"id_text":"P008001","period":{"period":"Proto-Elamite"}}\n',
             FakeHeaders()),
        ]

        def fake_fetch(url, **kwargs):
            payload, headers = pages.pop(0)
            return payload, headers

        def fake_normalize(raw, **kwargs):
            return {
                "artifact": {
                    "artifact_id": f"CDLI:{raw['id_text']}",
                    "period": "Proto-Elamite",
                }
            }

        with patch.object(ingest, "fetch_url", side_effect=fake_fetch), patch.object(
            ingest, "normalize_cdli_artifact", side_effect=fake_normalize
        ):
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "corpus.json"
                manifest = Path(tmp) / "manifest.json"
                count, _ = ingest.ingest(
                    host="https://cdli.earth",
                    output=output,
                    manifest=manifest,
                    min_count=2,
                    timeout=1,
                    retries=0,
                )
                self.assertEqual(count, 2)
                document = json.loads(output.read_text())
                self.assertEqual(
                    [r["artifact"]["artifact_id"] for r in document["records"]],
                    ["CDLI:P008001", "CDLI:P008002"],
                )
                self.assertEqual(document["dataset_status"], "frozen_metadata_snapshot")

    def test_duplicate_artifacts_fail_closed(self):
        payload = b'{"id_text":"P008001","period":{"period":"Proto-Elamite"}}\n{"id_text":"P008001","period":{"period":"Proto-Elamite"}}\n'

        def fake_fetch(url, **kwargs):
            return payload, FakeHeaders()

        def fake_normalize(raw, **kwargs):
            return {"artifact": {"artifact_id": "CDLI:P008001", "period": "Proto-Elamite"}}

        with patch.object(ingest, "fetch_url", side_effect=fake_fetch), patch.object(
            ingest, "normalize_cdli_artifact", side_effect=fake_normalize
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ingest.IngestionError, "duplicate"):
                    ingest.ingest(
                        host="https://cdli.earth",
                        output=Path(tmp) / "corpus.json",
                        manifest=Path(tmp) / "manifest.json",
                        min_count=1,
                        timeout=1,
                        retries=0,
                    )

    def test_page_at_limit_without_next_link_fails(self):
        payload = b"".join(
            f'{{"id_text":"P{800000+i:06d}","period":{{"period":"Proto-Elamite"}}}}\n'.encode()
            for i in range(ingest.PAGE_SIZE)
        )
        headers = FakeHeaders()

        def fake_fetch(url, **kwargs):
            return payload, headers

        def fake_normalize(raw, **kwargs):
            return {"artifact": {"artifact_id": f"CDLI:{raw['id_text']}", "period": "Proto-Elamite"}}

        with patch.object(ingest, "fetch_url", side_effect=fake_fetch), patch.object(
            ingest, "normalize_cdli_artifact", side_effect=fake_normalize
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ingest.IngestionError, "without a next-page link"):
                    ingest.ingest(
                        host="https://cdli.earth",
                        output=Path(tmp) / "corpus.json",
                        manifest=Path(tmp) / "manifest.json",
                        min_count=1,
                        timeout=1,
                        retries=0,
                    )

    def test_cdli_first_link_can_advance_a_full_page_when_next_is_missing(self):
        headers = FakeHeaders(['<https://cdli.earth/search?limit=1000&simple-field%5B0%5D=period&simple-value%5B0%5D=Proto-Elamite&simple-op%5B0%5D=AND&page=1>; rel="first"'])
        next_page = ingest.next_url(headers, "https://cdli.earth", 1, 1000, 1000)
        self.assertIn("page=2", next_page)
        self.assertIn("simple-field%5B0%5D=period", next_page)

    def test_hash_is_order_independent_after_sorting(self):
        records_a = [
            {"artifact": {"artifact_id": "CDLI:P008002"}},
            {"artifact": {"artifact_id": "CDLI:P008001"}},
        ]
        records_b = list(reversed(records_a))
        sorted_a = sorted(records_a, key=lambda r: r["artifact"]["artifact_id"])
        sorted_b = sorted(records_b, key=lambda r: r["artifact"]["artifact_id"])
        self.assertEqual(ingest.canonical_records_hash(sorted_a), ingest.canonical_records_hash(sorted_b))


if __name__ == "__main__":
    unittest.main()
