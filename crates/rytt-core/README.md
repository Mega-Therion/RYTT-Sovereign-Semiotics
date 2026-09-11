# rytt-core

JSON-first portable boundary for the RYTT sovereign semiotics grammar.

## Stages

1. **Contract surface (this scaffold).** Spec loading, PUA bound constants
   (`U+E020` / `U+E820`), versioned envelope types. The canonical spec is
   loaded via `include_str!` from `src/rytt/data/rytt-spec-v0.1.0.json`; the
   grammar is not vendored here.
2. **Chord mapping.** Implement `encode`/`decode` against the spec, then
   unignore the conformance replay test.
3. **Extraction.** Once the contract is stable, this crate can move to its
   own repository; downstream repos (chyren-selin, chyren-aeon) then depend on
   it rather than forking the grammar.

## Bounds

- Lower PUA compound boundary: `U+E020`
- Upper PUA compound boundary: `U+E820`

Tracked in https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/issues/6
