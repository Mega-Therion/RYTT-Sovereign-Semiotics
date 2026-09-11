# RYTT Sovereign Semiotics — Specification v0.1.0

> A formal, lossless, reversible grammar mapping language to radial glyph chords and dual-plane native tokens.

---

## 1. Overview

RYTT (pronounced "write") is a semiotic encoding system designed to represent natural-language text as a sequence of radial glyph primitives and chord ligatures assigned to Unicode Private Use Area (PUA) codepoints. The system is fully **lossless** and **reversible**: any source text encoded through the RYTT compiler can be recovered byte-for-byte via the decompiler.

---

## 2. Capability Map

| Capability | Status | Notes |
|---|---|---|
| 52-glyph Dual-Plane Genome (A–Z upper + a–z lower) | ✅ v0.1.0 | PUA `U+E000`–`U+E019` (lower) · `U+E800`–`U+E819` (upper) |
| Multi-length Chord Ligatures (2-, 3-, 4-letter) | ✅ v0.1.0 | Greedy longest-match |
| Lossless Round-Trip for ASCII + Unicode passthrough | ✅ v0.1.0 | Non-PUA chars pass through unchanged |
| Holonomic Multi-Base Tiers (Base 3 / 9 / 7 / 21) | ✅ v0.1.0 | Balanced ternary → septenary → bridge |
| 10 240-bit VSA Hypervector (BSC, SHA-512 expanded) | ✅ v0.1.0 | 20 × 512-bit ZMM SIMD layout |
| Installable Python Package + CLI | ✅ v0.1.0 | `rytt encode / decode / inspect` |
| Browser Playground (client-side, static) | ✅ v0.1.0 | `web/` served via Vercel |
| Lean4 Formal Proofs | 🔜 v0.2.0 | See `proofs/` scaffolding |
| Rust Native Re-implementation | 🔜 v0.3.0 | Performance tier |
| Manim Animation Suite | 🔜 v0.2.0 | See `manim/` scaffolding |

---

## 3. Encoding Architecture

### 3.1 Dual-Plane Genome

Every Latin letter maps to a unique PUA codepoint in one of two planes:

| Plane | Description | PUA Range | `elevation_z` |
|---|---|---|---|
| Ground Plane | Lowercase letters (a–z) | `U+E000`–`U+E019` | 0.0 |
| Elevated Plane | Uppercase letters (A–Z) | `U+E800`–`U+E819` | 25.0 |

Case polarity is embedded in the codepoint itself; no out-of-band marker is needed.

### 3.2 Chord Ligatures

High-frequency letter sequences are packed into single PUA codepoints via a **greedy longest-match** algorithm at compile time. Ligature lengths range from 2 to 4 characters. Both case variants (upper and lower) are defined for every ligature.

### 3.3 Passthrough Rule

Any character that is neither a Latin letter nor a space (digits, punctuation, symbols, non-Latin alphabets, newlines) is passed through to the encoded stream unchanged and decompiles to itself exactly.

---

## 4. Metric Boundary Guidance

| Metric | Definition | Interpretation |
|---|---|---|
| `compression_ratio` | `source_chars / token_count` | > 1.0 when chords reduce token count |
| `token_savings_pct` | `(1 − tokens/chars) × 100` | Tokens-vs-characters; **can be negative** — not clamped |
| `utf8_bytes_source` | Raw source UTF-8 byte length | Wire-size baseline |
| `utf8_bytes_encoded` | Encoded PUA UTF-8 byte length | PUA chars encode as 3 bytes each in UTF-8 |

> ⚠ **Important**: RYTT PUA codepoints are out-of-vocabulary for BPE tokenizers (tiktoken, sentencepiece). Each PUA char byte-falls-back to ≈ 3 BPE tokens, while typical English averages ≈ 4.9 chars/token. RYTT is **not** a BPE compression scheme; it is a semiotic re-representation layer.

---

## 5. Implementation Plan

| Milestone | Target | Scope |
|---|---|---|
| v0.1.0 | 2026-09-09 | Core compiler, CLI, browser playground, CI, invariant tests |
| v0.2.0 | TBD | Lean4 formal proofs of round-trip and PUA disjointness |
| v0.3.0 | TBD | Rust re-implementation with WASM build for browser |
| v0.4.0 | TBD | Extended ligature corpus (100+ chords), coverage analysis |

---

## 6. Canonical Machine-Readable Specification

The canonical grammar for each release is stored at `src/rytt/data/rytt-spec-v0.1.0.json`. It contains the complete dual-plane genome, chord records, PUA derivations, matching rule, plane constants, and metric constants. The Python compiler validates its executable records against this artifact at import time and fails closed on drift.

The browser module and vocabulary fixture remain generated projections. Run `python scripts/generate_web_data.py` after changing the canonical grammar or compiler implementation. CI verifies the generated projections and compiler invariants on every push. The Lean layer is not yet generated from this artifact; its constants remain a separate formal surface and are therefore an explicit remaining synchronization task.

The canonical artifact is versioned independently of prose. A semantic vocabulary change requires either updating the artifact and projections under the same release version or creating a new versioned artifact and updating the compiler's expected version.

---

*Authored by R.W. Yett — Chyren Sovereign Intelligence*
