# Changelog

All notable changes to **RYTT Sovereign Semiotics** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Display escape. U+0020, which no encoder otherwise emits, marks the next codepoint as literal. Source U+00B7 and the RYTT PUA range U+E000–U+F8FF are written behind it, so `decode(encode(text)) == text` now holds for every Unicode text in the Python reference, the Rust crate, and the web playground. Two new conformance vectors cover it: `escape_space_marker` and `escape_pua`.

### Changed

- Sources containing an unallocated PUA codepoint (in U+E000–U+F8FF but outside the 98 allocated ones) now encode with the escape. Before, Python passed them through unescaped and the Rust decoder rejected them; both now agree.
- No other output changed. The seven original conformance vectors are byte-identical, and the canonical spec files, their hashes, and `spec_version` are unchanged, so existing envelopes still verify.

## [0.2.0] — 2026-09-11

### Added

- Canonical machine-readable vocabulary at `spec/vocabulary.json`, schema contracts, format specification, and deterministic generators.
- Shared conformance vectors with executable replay verification and a documented formal-core boundary.
- Corrected standalone Lean PUA thresholds to align with the canonical `U+E020` and `U+E820` compound boundaries.
- Research-laboratory playground trace output showing candidate chords, selection decisions, token type, plane, codepoint, and exact recovery.
- Named-baseline benchmark arena with JSON and HTML reports that keep character, byte, RYTT-token, runtime, and optional tokenizer metrics separate.
- Portable JSON API boundary, versioned RYTT interchange envelope, offline ZIP artifact export, and tamper-detecting artifact verification.
- Codex Studio flagship workspace combining the browser compiler, research links, trace surface, and portable export.
- Research agenda, interoperability contract, operations guide, static accessibility audit, and performance smoke test.

### Changed

- Landing-page navigation now exposes Codex Studio and the Benchmark Arena.
- Browser playground has skip navigation, an explainable trace panel, named metric panel, and artifact export.
- CI now gates canonical generation, conformance, formal boundaries, artifact replay, benchmark arena, accessibility surface, and static deployment routes.
- Browser data generation derives its version from the package rather than hardcoded release text.
- README documents the platform architecture, artifact workflow, benchmark methodology, verification commands, and new public routes.

### Verification

- 45 automated tests passed.
- Canonical specification and conformance vector checks passed with deterministic hashes.
- Formal boundary alignment passed; standalone Lean compilation remains separately gated in GitHub Actions.
- Benchmark arena generated JSON and HTML reports; all seven corpora passed exact round-trip checks.
- Artifact export and offline verification passed, including a tamper-failure test.
- Static accessibility audit passed for the landing page, direct playground, and Codex Studio routes.
- Package wheel build passed for `rytt-sovereign-semiotics-0.2.0`.

---

## [0.1.0] — 2026-09-09

### Added

- Canonical `SPECIFICATION.md`, capability map, implementation plan, and versioned vocabulary fixtures.
- Installable Python package metadata with `rytt` CLI commands for `encode`, `decode`, and `inspect`.
- Browser playground for client-side compilation, token inspection, explicit metrics, and exact round-trip reporting.
- Generated `web/rytt-data.js` and `fixtures/rytt_vocabulary.json` derived from compiler definitions.
- Benchmark corpus covering prose, code, mixed casing, punctuation, whitespace, and Unicode passthrough.
- JSON benchmark output with separate character, token, byte, runtime, chord, and fidelity metrics.
- Property-style invariant tests for round-trip behavior, PUA disjointness, uniqueness, precedence, fixtures, and public interfaces.

### Changed

- Unsupported non-Latin alphabetic characters now pass through unchanged instead of falling back to the `A` glyph.
- Compilation result dictionaries now expose explicit source, token, byte, decoded, and character-reduction fields while retaining legacy fields.
- Glyph Atlas primitive PUA labels consume generated compiler data.
- README leads with specification, playground, installation, and metric-boundary guidance.

### Fixed

- `token_savings_pct` is no longer clamped and correctly reports negative values when RYTT produces more tokens than source characters.

### Verification

- 24 automated tests passed at the time of release.
- Wheel build, CLI smoke test, seven benchmark corpora, and local static route checks passed.

[0.2.0]: https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/releases/tag/v0.2.0
[0.1.0]: https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/releases/tag/v0.1.0
