# RYTT — Sovereign Semiotics

<p align="left">
  <a href="https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml"><img src="https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml/badge.svg" alt="RYTT CI"></a>
  <a href="https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/rytt-core-ci.yml"><img src="https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/rytt-core-ci.yml/badge.svg" alt="Rust Core CI"></a>
  <a href="https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/Lean%204-standalone%20verified-6f42c1?style=flat-square&logo=lean&logoColor=white" alt="Lean 4 Standalone Verified"></a>
  <a href="https://huggingface.co/datasets/ChyRho/rytt-sovereign-semiotics-benchmarks"><img src="https://img.shields.io/badge/Hugging%20Face-ChyRho%2Frytt-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="Hugging Face Dataset"></a>
  <a href="https://orcid.org/0009-0001-1303-7190"><img src="https://img.shields.io/badge/ORCID-0009--0001--1303--7190-A6CE39?style=flat-square&logo=orcid&logoColor=white" alt="ORCID"></a>
  <a href="https://resnova-hub-f4ucvy3e.manus.space"><img src="https://img.shields.io/badge/Research%20Atlas-resnova--hub-0070f3?style=flat-square&logo=safari&logoColor=white" alt="Research Atlas"></a>
  <a href="https://www.linkedin.com/in/r-w-yett/"><img src="https://img.shields.io/badge/LinkedIn-R.W._Yett-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="https://x.com/_chyrho_"><img src="https://img.shields.io/badge/X-@__ChyRho__-000000?style=flat-square&logo=x&logoColor=white" alt="X"></a>
</p>

A formal, lossless, reversible grammar mapping language to radial glyph chords and dual-plane native tokens.

## AI Safety & LLM Representation Research Utility

RYTT's core invariant — `decode(encode(text)) == text` with **zero discrepancy**, verified in Lean 4 and enforced by a Rust engine — makes it a direct research instrument for LLM safety and mechanistic interpretability:

- **Token representation auditing**: RYTT's dual-plane allocation (`U+E000` ground / `U+E800` elevated) provides a formal, human-readable semiotic layer over LLM token vocabularies, enabling systematic comparison between model-internal and human-legible representations
- **Lossless round-trip as a safety primitive**: `decode(encode(text)) == text` for every Unicode text. The two character classes the display stream reserves (U+00B7, the literal-space marker, and the RYTT PUA range U+E000–U+F8FF) are written behind a one-character escape, so they decode to themselves. The Lean proofs cover the PUA round-trip of the chord constructors on bounded domains; the full compiler is checked by the conformance vectors and tests
- **Sycophancy & drift detection benchmark**: The 7-vector conformance suite (`conformance/vectors.json`) provides a minimal, deterministic test harness for detecting when a model's token-processing behavior departs from the declared grammar — the same pattern used to catch evaluator-gaming in alignment evaluations
- **Formal Lean 4 standalone proof** (`proofs/RYTT_standalone.lean`): No Mathlib dependency; compiles in seconds on any CI runner and constitutes a machine-checkable certificate of the reversibility claim



## System Role & Authority

`RYTT-Sovereign-Semiotics` is the canonical owner and specification authority for the RYTT semiotic grammar, PUA allocation planes, and dual-plane token serialization.

- **Standalone Grammar**: Downstream projects (`4Leibniz`, `Res-Nova`, `MVPC-X`, `chyren-aeon`) consume RYTT via versioned JSON interfaces and bridge contracts. They do not fork, duplicate, or alter the token vocabulary.
- **Pure Reversibility**: The core invariant is zero-discrepancy round-trip (`decode(encode(text)) == text`) across all Unicode text. Source U+00B7 (the literal-space marker) and codepoints in the RYTT PUA range U+E000–U+F8FF are written behind the display escape ([SPECIFICATION.md §3.4](SPECIFICATION.md#34-display-escape)).
- **Dual-Plane Allocation**: Maps 52 genome bases and 46 ligatures across Private Use Areas:
  - Ground Plane: `U+E000` (`z = 0`)
  - Elevated Plane: `U+E800` (`z = 25`)

## Cross-Repository Coordination

- **4Leibniz (Issue #10)**: Bound via `integration/4leibniz_bridge.json` for symbolic notation and interchange of Lean theorem metadata.
- **Res-Nova (Issue #48)**: Ingests select manuscript passages strictly as benchmark corpora to evaluate compression and token density.
- **MVPC-X (Issue #7)**: Audits serialized token envelopes and executes independent conformance replay against `conformance/vectors.json`.

## Specification & Conformance

- **Specification**: `src/rytt/data/rytt-spec-v0.1.0.json`
- **Conformance Suite**: 7 standard test vectors in `conformance/vectors.json` verifying:
  - Empty string
  - Mixed-case ASCII
  - Chord-rich English
  - Whitespace preservation
  - Symbol preservation
  - Unicode passthrough
  - Comprehensive character sets
- **Rust Engine**: High-performance WASM and native core in `crates/rytt-core`.

## Verification

```bash
# Run pytest verification suite
pytest tests/

# Validate conformance vectors
python -m rytt.cli verify conformance/vectors.json
```
