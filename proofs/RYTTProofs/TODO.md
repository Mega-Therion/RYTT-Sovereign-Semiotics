# Proof TODO — tracked work items

## RETRACTED (2026-09-09): the "Completed in v0.3.0" section below is false

Commit `71bc723` ("feat(proofs): complete formal suite") claimed everything in the
section below as proved. It was never verified: the repo shipped with **no
`lean-toolchain` file** (a fresh checkout could not even select a Lean version),
**no lake manifest**, an **unpinned Mathlib `require`** in `lakefile.lean`, and CI
(`.github/workflows/ci.yml`) has only ever run the Python test suite — it does not
invoke `lake build` and never has.

On 2026-09-09 this was actually built for the first time, against
`leanprover/lean4:v4.33.0-rc1` + Mathlib pinned to the same revision Res-Nova
already verifies against (`5eec30bc56ed5a23be2e27c544a949ba0bceddeb`). Results:

- `lakefile.lean` did not parse under real Lake (`name` is not a valid
  `PackageConfig` field when `package rytt where` already names it; `version`
  needs a `StdVer` literal, e.g. `v!"0.2.0"`, not a bare string). Fixed.
- `RYTT.lean` put its module docstring *before* the `import` lines, which Lean
  rejects outright. Fixed (docstring moved after imports).
- With both of those fixed, `RYTT.lean` alone — the base module every
  `RYTTProofs/*.lean` file imports — has **at least 10 independent compile
  failures**: several `omega`-tactic failures on the claimed character-range
  arithmetic (i.e. the stated bounds do not actually follow), a syntax error
  (`unexpected token '/--'`), unsolved goals including a literal `⊢ False`,
  and a reference to `Nat.iterate_add`, which does not exist in this Mathlib.
- The seven `RYTTProofs/*.lean` files (`Compiler.lean` — which contains the
  claimed `compile_decode_roundtrip` round-trip theorem — plus `Chords`, `VSA`,
  `Leibniz`, `Holonomic`, `Parity`, `Integration`) all `import RYTT`, so none of
  them can even be attempted until `RYTT.lean` compiles clean. **None have been
  checked.**

No `sorry` appears anywhere in these files, but that is not evidence of
correctness here — the files do not type-check, which is a stronger failure
than a `sorry`-laden but type-correct proof would be. Every `[x]` below is
unverified and should be read as `[ ]` until re-proved against a real build.

## Completed in v0.3.0 — UNVERIFIED, see retraction above

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
