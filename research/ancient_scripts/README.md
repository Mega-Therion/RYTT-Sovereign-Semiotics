# Ancient-script comparative research contract

This is a research extension, not a claim that RYTT deciphers Proto-Elamite.

- `schema/claim-record-v0.1.0.schema.json`: JSON Schema contract.
- `samples/cdli-proto-elamite-sample.json`: CDLI P008001 and P008002 metadata only; no images, observations, or interpretations.
- `../../scripts/validate_ancient_script_records.py`: standard-library validator for key invariants.
- `../../tests/test_ancient_script_records.py`: positive and negative tests.

Keep catalog metadata, direct observations, and interpretive claims separate. Treat hypothetical sign values as hypotheses, not ground truth. Keep Proto-Elamite and Linear Elamite separate unless supported by documented scholarship. Freeze data versions, preprocessing, held-out splits, and baselines before evaluation.

No artifact images are included. Public visibility is not permission to mirror images; review CDLI terms and per-image rights before reuse. Metadata rights also require review.

Catalog entries checked 2026-10-08: [P008001](https://cdli.earth/search?id=P008001&layout=compact), [P008002](https://cdli.earth/search?id=P008002&layout=compact). Recheck live records before reuse.

Run from repository root: `python scripts/validate_ancient_script_records.py` and `pytest tests/test_ancient_script_records.py`.


## Current implementation

The current pilot also includes a CDLI metadata normalizer, a source-linked observation fixture, an artifact-level leakage-check fixture, and an external baseline replication plan. None of those artifacts asserts a decipherment result.
