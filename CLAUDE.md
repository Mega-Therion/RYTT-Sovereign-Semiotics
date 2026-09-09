# CLAUDE.md — RYTT Sovereign Semiotics

Guidance for Claude Code working in this repository.

## Lean proofs — read before touching `proofs/`

`proofs/` claims a "complete formal suite" (commit `71bc723`) covering the round-trip
identity, chord injectivity, VSA quasi-orthogonality, the 4Leibniz chain rule, holonomic
path algebra, and parity homomorphism. **That claim is false.** As of 2026-09-09 it had
never been built: no `lean-toolchain`, no lake manifest, an unpinned Mathlib `require`,
and CI (`.github/workflows/ci.yml`) has only ever run the Python suite — it does not
invoke `lake build`.

A real build was attempted for the first time on 2026-09-09, pinned to
`leanprover/lean4:v4.33.0-rc1` with Mathlib at `5eec30bc56ed5a23be2e27c544a949ba0bceddeb`
(the same revision Res-Nova already verifies against — its `.lake/packages/` cache can
be symlinked in to avoid an ~8GB refetch). `lakefile.lean` didn't parse (invalid
`PackageConfig` field, wrong `version` literal type) and `RYTT.lean` had its module
docstring before the `import` lines (also a parse error) — both fixed. Past that,
`RYTT.lean` alone has **at least 10 independent compile failures**: failing `omega`
arithmetic on the claimed character-range bounds, a syntax error, unsolved goals
(including a literal `⊢ False`), and a reference to a Mathlib lemma that doesn't exist.
The seven `RYTTProofs/*.lean` files all import `RYTT` and have never been reached.

No `sorry` appears anywhere — this is not the usual "sorry-free but vacuous" failure
mode, it's one level worse: the files do not type-check at all. Full details and status
tracking live in `proofs/RYTTProofs/TODO.md`; treat every `[x]` there as unverified
until it is re-proved against a real build. Do not cite these theorems as established,
and do not add new work on top of `RYTTProofs/*.lean` without first getting `RYTT.lean`
itself past `lake build`.

`sorry`-free is not the same as substantive, and now it isn't even the same as
compiling. The test is **substitutability**: replace the semiotics in a statement with
nonsense and see whether the same proof still closes.

## CI

`.github/workflows/ci.yml` runs the Python suite (pytest, benchmarks, CLI smoke test)
across Python 3.10–3.12. It does not build or check `proofs/` in any way; a red Lean
build will not be caught by CI as it currently stands.
