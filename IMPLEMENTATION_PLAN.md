# RYTT End-to-End Implementation Plan

## Stage A — Canonical system

Create `spec/rytt.schema.json`, `spec/vocabulary.json`, and `spec/format.md`. Generate Python, browser, fixture, and Lean-facing tables from the canonical vocabulary. Add a schema version and vocabulary hash to every generated artifact.

**Done when:** changing a mapping in the source vocabulary regenerates every consumer, stale generated files fail CI, and the fixture hash is identical across Python and browser consumers.

## Stage B — Conformance and proof

Create shared JSONL vectors for primitive glyphs, chords, passthrough text, mixed casing, malformed streams, and version metadata. Add Python conformance tests, browser replay tests, and a Lean theorem report that documents exactly which token algebra is verified.

**Done when:** all implementations pass the same vectors and the CI log records the specification version, vocabulary hash, and formal theorem status.

## Stage C — Research laboratory

Extend the browser playground into a lab with compile, trace, compare, geometry, proof-status, and export panels. Every token decision must be explainable, including rejected chord candidates and passthrough rationale.

**Done when:** a visitor can enter text, inspect all decisions, compare named metrics, download a JSON trace, and replay the same trace locally.

## Stage D — Benchmark arena

Add versioned public corpora, tokenizer adapters that are optional and clearly named, runtime and memory measurements, raw JSON output, an HTML report, and negative-result commentary. No aggregate score may combine incompatible units.

**Done when:** one command recreates the report, every row names its tokenizer and corpus, and the report remains useful when RYTT loses.

## Stage E — Portable core and interchange

Define an implementation-neutral core API and a versioned `.rytt` container. Implement Python JSON encoding first, then a WASM-compatible boundary or equivalent browser module. Include checksums, vocabulary identity, source encoding, passthrough segments, and corruption diagnostics.

**Done when:** an artifact created by the CLI can be opened by the browser and an artifact created by the browser can be replayed by the CLI.

## Stage F — Verified artifact export

Export a self-contained directory or ZIP with source, encoded stream, token trace, metrics, SVG rendering, verification status, package/spec versions, and a replay README. Add a verifier command that exits nonzero on mismatch.

**Done when:** an exported bundle can be moved to a clean directory and verified without network access.

## Stage G — Codex Studio

Build a focused authoring workspace around source text, token geometry, trace inspection, and evidence export. Keep it static and local-first initially. Add persistent storage only after the single-user workflow is excellent.

**Done when:** Create → compile → inspect → edit → export → replay is a coherent keyboard-accessible flow.

## Stage H — Hardening and release

Run accessibility checks, performance checks, security-header checks, mobile checks, package builds, browser route smoke checks, formal proof gates, and reproducibility checks. Publish `0.2.0`, `0.3.0`, and `0.4.0` only when their gates pass.
