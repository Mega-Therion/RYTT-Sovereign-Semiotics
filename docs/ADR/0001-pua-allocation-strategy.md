# ADR 0001: PUA Allocation Strategy

## Status

Accepted (2026-09-28)

## Context

The RYTT grammar assigns its symbolic alphabet to the Unicode BMP Private
Use Area (U+E000–U+F8FF). Unmanaged PUA allocation can cause character
collisions across host environments — operating systems, terminal emulators,
and commercial fonts frequently map glyphs into this range without
centralized coordination.

## Decision

Define two transport profiles:

1. **Direct PUA Profile** — for closed runtimes, tokens are represented
   directly as PUA code points. Mappings are registered with the ConScript
   Unicode Registry (UCSUR) to document allocation boundaries.

2. **Escaped Interchange Profile** — for external data exchange, tokens are
   represented as structured JSON envelopes or remapped into Supplementary
   PUA-A (U+F0000–U+F00FF).

CSS `@font-face` with `unicode-range` declarations isolates custom fonts
to precise codepoint ranges, preventing cross-contamination with host
font substitutions.

## Allocation Sectors

| Sector | Range | Cardinality | Mitigation |
|--------|-------|-------------|-----------|
| Ground Plane (z=0) | U+E000–E033 | 52 | CSS unicode-range, UCSUR |
| Ground Ligatures | U+E020–E04D | 46 | Structured escape |
| Elevated Plane (z=25) | U+E800–E833 | 52 | CSS unicode-range, UCSUR |
| Elevated Ligatures | U+E820–E84B | 46 | Structured escape |
| Reserved Extension | U+E82E–E8FF | 210 | Schema validation error in v0.1.0 |
| Extended PUA Fallback | U+F0000–F00FF | 256 | Dynamic offset table |

## Consequences

- Closed runtimes get direct PUA access with font isolation.
- External environments use JSON envelopes or Supplementary PUA-A.
- The reserved extension block triggers schema validation errors until
  a minor release formally assigns it.
- Plane disjointness is formally verified in Lean 4 (`plane_partition_disjoint`).
