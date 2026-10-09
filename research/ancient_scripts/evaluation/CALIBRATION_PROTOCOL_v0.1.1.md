# Known-key calibration protocol v0.1.1

**Frozen 2026-10-08, before any claim-generating method has been run on any corpus.** It supersedes `CALIBRATION_PROTOCOL_v0.1.0.md`, which stays as the frozen record. Every change below comes from a pre-run red team (a referee-panel agent). Each scorer change is tested in `tests/test_claim_calibration.py` and was sabotage-checked on copies.

## Why the change
v0.1.0 would have certified bad methods:
- **Tiny assertion sets passed.** A method asserting just 2 correct values out of an 87-sign key passed (p = 0.0003, FDR 0).
- **The null could be gamed.** Shuffling over the whole key let unasserted entries inflate it: one correct assertion failed at K = 87 and passed at K = 187.
- **No declaration point.** A method could pick its threshold after seeing the results.
- **The key leaked.** Unicode itself names U+10000 "LINEAR B SYLLABLE B008 A".

All four were reproduced against the v0.1.0 scorer before this version was written.

## Order (each step requires the previous one)
1. **Pipeline check**: replicate Born et al. (Findings of ACL 2021).
   - It is a compositionality study and emits no sign→value output, so it checks the pipeline. It cannot feed step 2.
2. **Known-key calibration** (this protocol).
3. **Proto-Elamite scoring.** Passing step 2 licenses nothing until a step-3 protocol, with its own metric, is frozen.

## Declaration (required; the scorer refuses to run without it)
Before first scoring, commit a declaration file with four fields:
- `method_commit`
- `control_id`
- `threshold`
- `assertions_sha256`

The scorer checks the assertions file against the hash. It appends every run to a log, and **only the first run per (method_commit, control_id) counts**; later runs are marked `counts: false` and reported. The declared threshold is the one used at step 3.

## Control
- **Key class:** the key holds only attested, value-known signs of one class. Undeciphered signs, ideograms, numerals and dual-function signs (syllabogram/logogram) are excluded and listed.
- **Normalization:** values are compared after NFC, casefold and trim. The manifest lists the accepted alternatives per sign (e.g. a2/ha). The key may give a list of strings, and anything else is rejected.
- **Leakage controls:**
  - Signs are re-encoded per run as salted random integers.
  - The key stays outside a no-network sandbox.
  - The method is frozen before the control is opened.
  - Pretrained methods must also pass a fresh-key cipher of text written after their training cutoff. The worse of the two results gates, and the gap is reported as contamination.
- **Difficulty matching.** Linear B (~87 syllabic signs, known language) does not stand in for Proto-Elamite (~1,900 non-numerical signs, ~1,050 hapax, unknown language, accounting use).
  - A synthetic control matched to the frozen snapshot is required: ≥ 1,000 sign types, ≥ 50% hapax, matched token count and numeral share, and no related-language lexicon.
  - FDR is reported by sign-frequency band, and Proto-Elamite claims are admissible only in bands that passed.

## Scoring (`score_claims.py`, protocol string `known-key-calibration/0.1.1`)
- **Input.** One assertion per sign; duplicates are rejected. Confidences must be numbers in [0, 1], and booleans are rejected. Signs absent from the key are counted and excluded.
- **Basic counts.** m is the number of scorable assertions and hits the number that match. The measured FDR is (m − hits)/m.
- **FDR bound.** Its one-sided 95% Clopper–Pearson upper bound is reported. At 0 errors it falls to 0.20 only from m = 14.
- **Permutation null.**
  - The asserted signs are re-paired with the key entries of the asserted signs only, so padding the key can't move p.
  - Signs are sorted first, so key order can't move p either.
  - Settings: N = 10,000 shuffles, seed 20261008.
- **p-value and inconclusive band.** p = (1 + #{null ≥ hits})/(N + 1). If |p − 0.01| < 3 SE, the result is **inconclusive** (exit 3), unless another criterion already fails.
- **Exit codes.**
  - 0: pass;
  - 1: fail;
  - 2: bad input, including no scorable assertion or a crash;
  - 3: inconclusive.

The inputs' sha256 values are reported.

## Gate
A method is admissible for step 3 only if **all** hold at its declared threshold, on the matched control:
- p < 0.01;
- FDR upper bound ≤ 0.20;
- its FDR upper bound is below the measured FDR of the frozen **frequency-rank baseline** on the same control. The baseline pairs signs and values by descending frequency rank, ties broken by name, as in `frequency_rank_baseline()`; cf. Ravi & Knight 2008.

Failed calibrations are results and are kept.

## Not adopted from the red team
- **Exact p.** Using the exact p for unique-valued keys is not adopted: under the asserted-sign null the exact distribution is a restricted-permutation count. The Monte Carlo p with its SE band is used instead.

## Tests
`tests/test_claim_calibration.py` has 14 tests, all on synthetic keys. They check:
- a perfect method passes;
- 2-of-2 fails;
- the minimum m at 0 errors is 14;
- padding the key and reordering it don't change p;
- random, modal-value and frequency-rank methods all fail;
- a method must beat the baseline;
- normalization and alternatives work;
- bad inputs are rejected;
- declaration hashing and the first-run-counts log work;
- the inconclusive band;
- runs are deterministic.

Sabotage on copies (each made the suite exit 1):
- the old all-key null: 2 tests fail;
- the FDR point estimate in place of the bound: 1 fails;
- normalization removed: 1 fails;
- the declaration hash not checked: 1 fails.
