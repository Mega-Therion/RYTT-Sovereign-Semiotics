# Contributing to RYTT Sovereign Semiotics

Thank you for contributing to the RYTT Sovereign Semiotics specification and
reference implementations. This guide outlines repository organization and
the process for proposing changes.

## Repository Organization

| Directory | Purpose |
|-----------|---------|
| `crates/rytt-core` | Rust reference engine (codec, spec, WASM, C ABI, PyO3) |
| `src/rytt` | Python distribution (compiler, tokenizer, benchmarks) |
| `proofs/` | Lean 4 formal specifications and machine-checked proofs |
| `web/` | Web playground, chord renderer, WASM bindings, data |
| `conformance/` | Conformance vectors and JSON schema |
| `spec/` | Canonical specification artifacts |
| `benchmarks/` | Performance benchmarking suite |
| `supabase/functions/` | Edge function telemetry service |
| `integration/` | Cross-repository bridge contracts |

## Development Setup

```bash
# Python runtime
pip install -e ".[dev]"
pytest tests/

# Rust core
cd crates/rytt-core
cargo test

# Lean proofs (standalone, no Mathlib)
cd proofs
lean RYTT_standalone.lean
lean RYTT_sovereign.lean
```

## Architectural Decision Records (ADRs)

Modifications to any of the following require an Architectural Decision Record:

- PUA code point ranges or allocation sectors
- Ligature structures or genome base assignments
- Plane displacement constants (z=0, z=25)
- Inter-repository bridge contracts
- Binary wire protocol or envelope format

ADRs are stored in `docs/ADR/` and numbered sequentially. See
`docs/ADR/0001-pua-allocation-strategy.md` for the format.

## Semantic Versioning

- **Patch (1.0.x):** Bug fixes, performance, docs.
- **Minor (1.x.0):** Additive backward-compatible expansions (new ligatures in reserved block).
- **Major (x.0.0):** Breaking changes (genome bases, plane constants, wire protocol).
  Deprecated features remain functional for two minor cycles.

## Governance Phases

See `docs/PUA_ALLOCATION.md` for the full governance phase table. All
specification changes must pass through: Draft → Active Review →
Implementation → Formal Verification → Standardization.

## Testing

- **Conformance:** `cargo test --test conformance` (Rust) and `python scripts/verify_conformance.py` (Python)
- **Property fuzzing:** `cargo +nightly fuzz run roundtrip` (Rust) and `pytest tests/test_fuzz_hypothesis.py` (Python)
- **Lean proofs:** `lean proofs/RYTT_standalone.lean` and `lean proofs/RYTT_sovereign.lean`
- **Benchmarks:** `python benchmarks/run_benchmarks.py`

## CI

- `.github/workflows/ci.yml` — Python suite, conformance, CLI smoke
- `.github/workflows/rytt-core-ci.yml` — Rust core, WASM, benchmark parity
- `.github/workflows/ci-matrix.yml` — Multi-OS Rust + Python matrix, fuzzing
- `.github/workflows/lean-proofs.yml` — Lean 4 formal proof verification
