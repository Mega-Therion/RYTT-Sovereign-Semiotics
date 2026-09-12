# rytt-core

The Rust implementation of the JSON-first portable boundary for the RYTT sovereign semiotics grammar.

## Contract

The canonical grammar remains `src/rytt/data/rytt-spec-v0.1.0.json`. This crate loads it with `include_str!`; it does not duplicate or fork vocabulary data.

- **Greedy-longest-match** selection across 52 genome entries and 46 ligatures
- Lowercase ground plane: `z = 0`, base `U+E000`
- Uppercase elevated plane: `z = 25`, base `U+E800`
- Configured space display token: `·`
- Non-letter Unicode: unchanged passthrough
- Envelope integrity: canonical raw-artifact BLAKE3 vocabulary hash plus spec-version validation
- Unknown PUA codepoints: rejected during decode

## Verification

`tests/conformance.rs` replays every record in `conformance/vectors.json`: exact encoded display, token count, and inverse recovery. GitHub Actions runs `cargo test` and `cargo clippy` whenever the crate, canonical spec, or vector file changes.

## Next Boundary

After CI passes and the API is externally reviewed, extract `rytt-core` into a versioned standalone Cargo repository. `chyren-selin` and `chyren-aeon` consume it as a dependency; neither vendors the grammar.

Tracked in https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/issues/6
