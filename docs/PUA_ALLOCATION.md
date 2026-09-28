# PUA Allocation Governance — RYTT Sovereign Semiotics

## Overview

The RYTT grammar assigns its symbolic alphabet to the Unicode Basic
Multilingual Plane (BMP) Private Use Area (U+E000–U+F8FF). This document
defines the allocation strategy, collision mitigation, and transport
profiles to prevent conflicts with host environments.

## Allocation Sectors

| Sector | Code Point Range | Cardinality | Semantic Target | Mitigation |
|--------|------------------|-------------|-----------------|------------|
| Ground Plane (z=0) | U+E000 – U+E033 | 52 | Primary genome bases (A–Z, a–z) | CSS unicode-range isolation, UCSUR coordination |
| Ground Ligatures | U+E020 – U+E04D | 46 | Chord ligatures (lowercase) | Structured escape profiles |
| Elevated Plane (z=25) | U+E800 – U+E833 | 52 | Uppercase genome bases | CSS unicode-range isolation |
| Elevated Ligatures | U+E820 – U+E84B | 46 | Chord ligatures (uppercase) | Structured escape profiles |
| Reserved Extension | U+E82E – U+E8FF | 210 | Future operations & plane expansions | Reserved; triggers schema validation error in v0.1.0 |
| Extended PUA Fallback | U+F0000 – U+F00FF | 256 | Host environment remapping | Dynamic offset table for resolving host font collisions |

## Transport Profiles

### Direct PUA Profile (Closed Runtimes)

For closed runtimes where the font and rendering pipeline are fully
controlled, tokens are represented directly as PUA code points. The
system registers its mappings with the ConScript Unicode Registry (UCSUR)
to document allocation boundaries and avoid overlapping script assignments.

### Escaped Interchange Profile (External Environments)

For external data exchange, tokens are represented as structured JSON
records (the `Envelope` format) or remapped into Supplementary Private Use
Area-A (U+F0000–U+F00FF), where collisions are far less common.

## CSS Font Isolation

```css
@font-face {
  font-family: 'RYTT-Sovereign-Base';
  src: url('/fonts/rytt-ground.woff2') format('woff2');
  unicode-range: U+E000-E033;
  font-display: block;
}

@font-face {
  font-family: 'RYTT-Sovereign-Elevated';
  src: url('/fonts/rytt-elevated.woff2') format('woff2');
  unicode-range: U+E800-E82D;
  font-display: block;
}
```

The `unicode-range` declaration restricts the custom font to precise
codepoint ranges, preventing the browser from using the RYTT font for
surrounding text or applying system font fallbacks to RYTT tokens.

## Semantic Versioning Policy

- **Patch releases (1.0.x):** Internal bug fixes, performance optimizations,
  non-normative documentation updates.
- **Minor releases (1.x.0):** Additive, backward-compatible expansions
  (e.g., new ligatures within the reserved PUA block U+E82E–U+E8FF).
- **Major releases (x.0.0):** Breaking changes — alterations to the 52
  genome bases, plane displacement constants (z=0 or z=25), or binary wire
  protocol. Deprecated features remain functional for two minor cycles.

## Governance Phases

| Phase | Gate | Deliverables | Criteria |
|-------|------|-------------|----------|
| 0: Draft | RFC via PR | Initial RFC markdown, semiotic rationale | Documented rationale, identified target plane sector |
| 1: Active Review | Architectural review | PUA collision analysis, downstream impact report, Lean 4 model | Maintainer approval, UCSUR registry check |
| 2: Implementation | Reference engine merge | crates/rytt-core impl, conformance vectors, fuzz targets | Passing property tests, zero benchmark regressions |
| 3: Formal Verification | Machine-checked proofs | Verified Lean 4 theorems (reversibility, plane disjointness) | Zero-axiom build in CI, no unproven goals |
| 4: Standardization | Spec version cut | rytt-spec-v1.x.x.json, versioned SDKs | Stable tagged release across PyPI, npm, crates.io |
