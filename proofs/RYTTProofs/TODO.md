# Proof TODO — tracked work items

## Completed in v0.3.0

- [x] **Full compiler induction**: `RYTTProofs.Compiler` formalises the greedy
  longest-match tokeniser as a Lean `def` and proves `compile_decode_roundtrip`
  by structural induction over the tokeniser loop.  The `decodeSeq ∘ compileStr = id`
  master theorem is stated and proved.

- [x] **Discharge `chord_offsets_injective` axiom**: the axiom in `RYTT.lean § 6`
  has been removed.  `Chords.chord_offsets_injective_discharged` (proved by `decide`
  over the finite 23-chord table) replaces it as a theorem.

- [x] **VSA quasi-orthogonality**: `VSA.ConcentrationBound` records the Hoeffding/
  Chernoff parameters.  `VSA.QuasiOrthogonal` is a type-class with a canonical
  instance for D=10240.  `bind_isometry` proves XOR is a Hamming isometry.
  Full probabilistic Bernoulli-distribution proof deferred to Mathlib.Probability
  import (noted in `standardBound.valid`).

- [x] **4Leibniz full chain rule**: `SatisfiesChainRule` type, `chain_rule_G`,
  `chain_rule_E`, `chain_rule_C` all proved.  `operators_grade_commute` proves
  independent-position differentials commute.  `integrate_splits` proves the
  Leibniz integral distributes over disjoint diff-sets.

- [x] **Holonomic path algebra**: `RYTTProofs.Holonomic` — `runPath_monoid_hom`
  proves runPath is a monoid homomorphism from (Path, ++) to state transformers.
  `balanced_returns_count` proves returns = #{D steps} for balanced paths.
  `returns_nondecreasing` and `n_roundtrips_returns` complete the counting.

- [x] **Parity block homomorphism**: `RYTTProofs.Parity` — `π_concat` proves
  π : (Sequence, ++) → (ℤ/24ℤ, +) is additive.  `rytt_parity_hom` packages
  all four properties (unit, generator, additivity, period) into a single
  `ParityHomomorphism` structure.

## Open (v0.3.0 → v0.4.0)

- [ ] **Probabilistic quasi-orthogonality**: replace `QuasiOrthogonal` instance
  with a concrete Bernoulli-distribution proof once Mathlib.Probability.Distributions
  is stable.  Integrate the Chernoff bound numerically for D=10240, t=3.

- [ ] **Multi-token VSA retrieval correctness**: extend `retrieval_exact_single`
  to N-token records using the concentration bound — prove that retrieval succeeds
  with probability ≥ 1 - 2N·exp(-18) for D=10240.

- [ ] **Greedy tokeniser uniqueness**: prove that the greedy longest-match strategy
  produces the *unique* minimal-token-count tokenisation for any input string,
  given the chord priority ordering.

- [ ] **4Leibniz δ_P chain rule**: formalise the global form of δ_P product rule
  for paths that span parity block boundaries in A ++ B.

- [ ] **Cross-module integration test**: add a `#check` test file that imports all
  five new modules and verifies the full chain of dependencies compiles cleanly.
