# Known-key calibration protocol v0.1.0

> **Superseded 2026-10-08 by `CALIBRATION_PROTOCOL_v0.1.1.md`**, before any run. A pre-run red team showed this version would certify a 2-of-2 method and could be gamed by key padding and late threshold choice. Kept unchanged below as the frozen record.

**Frozen 2026-10-08, before any claim-generating method has been run on any corpus.** No method exists in this repository yet. Changing anything below needs a new protocol version, committed before the run it governs.

## Why
A method that proposes sign values for an undeciphered script can't be checked against the truth, because nobody has it. Running the same method first on a **control** whose key is known shows how often it is wrong, before any Proto-Elamite claim is scored. This is the same step as calibrating a scanner on control objects with known contents.

## Order (each step requires the previous one)
1. **Baseline replication**: Born et al. (Findings of ACL 2021), per item 4 of `README.md`. Not done yet.
2. **Known-key calibration** (this protocol). The method gets the control corpus with the key withheld and emits sign→value assertions.
3. **Proto-Elamite scoring** against the frozen split (`manifests/proto-elamite-full-split-v0.1.0.json`). This step is only for methods that passed step 2.

## Control
- A corpus with a published key. The candidate is Linear B with its standard syllabic values; a substitution cipher of a known-language corpus is an alternative.
- Which control, and its source and licence, are fixed in a control manifest committed before the first calibration run. That manifest is not part of v0.1.0.
- The key is never given to the method. The method's input is hashed and recorded in each claim's `method.input_hash`.

## Assertions and scoring (`score_claims.py`)
- **Input:** a list of assertions `{"sign", "value", "confidence"}`. A sign may be asserted only once; duplicates are rejected, since asserting every value for one sign would buy hits.
- **Unscorable:** assertions for signs absent from the key are counted separately and excluded from scoring.
- **hits:** scorable assertions whose value equals the key's value. **m:** the number of scorable assertions.
- **Measured FDR:** (m − hits) / m. The key is known, so this is measured, not estimated.
- **Permutation null:** the key's values are shuffled across all key signs, which preserves how often each value occurs. Hits are recomputed for the same assertions. This uses N = 10,000 shuffles with `random.Random(seed)`, seed 20261008.
- **p-value:** (1 + #{null hits ≥ hits}) / (N + 1).
- **Report:** m, hits, unscorable count, measured FDR, null mean, null 95th percentile, p, and the same quantities at confidence thresholds 0.5, 0.7 and 0.9 (assertions with `confidence` below the threshold dropped; a missing `confidence` counts as 0).

## Gate (fixed now)
A method is admissible for step 3 only if, on the control, at its own declared threshold, **both** hold:
- p < 0.01;
- measured FDR ≤ 0.20.

Both numbers are reported whether or not the method passes. A failed calibration is a result and is kept.

## Not covered by v0.1.0
- **Functional readings:** claims that are not one-to-one sign→value (ideograms, numerals, composites). They need their own key format and protocol.
- **Proto-Elamite FDR:** calibration bounds a method's error rate on the control. It doesn't measure that rate on Proto-Elamite. A control that is easier than Proto-Elamite makes the bound optimistic. Control difficulty (sign-inventory size, corpus size) must be reported beside the result.

## Tests
`tests/test_claim_calibration.py` runs the scorer on a **synthetic** key generated in the test (not evidence of anything) and checks:
- a perfect method passes the gate;
- a random method fails it;
- duplicates are rejected;
- unscorable signs are excluded;
- runs are deterministic.

The checks were proved load-bearing by sabotage on a copy (record in the PR).
