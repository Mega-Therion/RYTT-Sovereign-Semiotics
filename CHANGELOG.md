# Changelog

All notable changes to **RYTT Sovereign Semiotics** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-09-09

### Added

- Canonical `SPECIFICATION.md`, capability map, implementation plan, and versioned vocabulary fixtures.
- Installable Python package metadata (`pyproject.toml`) with `rytt` CLI commands for `encode`, `decode`, and `inspect`.
- Browser playground (`web/`) for client-side compilation, token inspection, explicit metrics, and exact round-trip reporting.
- Generated `web/rytt-data.js` and `fixtures/rytt_vocabulary.json` derived from compiler definitions via `scripts/generate_web_data.py`.
- Benchmark corpus covering prose, code, mixed casing, punctuation, whitespace, and Unicode passthrough.
- JSON benchmark output with separate character, token, byte, runtime, chord, and fidelity metrics.
- Property-style invariant tests (`tests/test_invariants.py`) for round-trip behavior, PUA disjointness, uniqueness, precedence, fixtures, and public interfaces.
- CI: package installation, generated-data verification, complete test execution, benchmark artifact upload, and static route checks.

### Changed

- Unsupported non-Latin alphabetic characters now pass through unchanged instead of falling back to the `A` glyph.
- Compilation result dictionaries now expose explicit `source_text`, `token_count`, `utf8_bytes`, `decoded_text`, and `character_reduction` fields while retaining legacy fields.
- Glyph Atlas primitive PUA labels consume generated compiler data (via `web/rytt-data.js`).
- README now leads with specification, playground, installation, and metric-boundary guidance.

### Fixed

- `token_savings_pct` is no longer clamped with `max(0.0, ...)`. The metric now correctly reports negative values when RYTT produces more tokens than the source character count. A pytest guard enforces the unclamped behaviour going forward.

### Verification

- 24 automated tests passed (`tests/test_invariants.py`).
- Wheel build passed for `rytt-sovereign-semiotics-0.1.0`.
- CLI `encode`/`decode` smoke test passed.
- Seven benchmark corpora passed exact round-trip checks.
- Local static route smoke checks passed.

---

[0.1.0]: https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/releases/tag/v0.1.0
