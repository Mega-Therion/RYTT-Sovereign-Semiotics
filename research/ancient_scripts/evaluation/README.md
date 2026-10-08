# Evaluation protocol

The Proto-Elamite evaluation protocol is intentionally staged:

1. A frozen metadata snapshot is the corpus source. The current frozen snapshot contains 1,755 canonical CDLI artifact IDs and is identified by SHA-256.
2. The held-out split is deterministic and bound to that exact snapshot hash. The split is artifact-level, with no duplicate or cross-split assignment.
3. Labels and preprocessing are separate. A frozen split does not imply that a task, label source, or preprocessing pipeline has been frozen.
4. Baseline replication precedes any RYTT experimental condition.
5. Positive and negative results are retained. A performance improvement is evidence about the evaluated computational task, not evidence of decipherment.

The committed holdout manifest identifies the exact GitHub Actions artifact used as the source snapshot. Do not replace it with a newer live CDLI export without creating a new snapshot hash and a new split manifest version.

Current split:
- train: 1,386
- validation: 200
- test: 169

The full assignment list is intentionally regenerated from the frozen snapshot rather than committed here. This keeps the repository from becoming a second corpus mirror while preserving deterministic assignment through the generator and assignment hashes.

Baseline target: Born et al. (Findings of ACL 2021), with the SFU implementation used as a replication target rather than a source of ground-truth Proto-Elamite readings.
