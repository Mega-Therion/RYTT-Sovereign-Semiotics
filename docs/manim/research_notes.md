# RYTT Visual Build Notes

## Framework decision

Use **Manim Community Edition (ManimCE)**. The requested outcome is a reproducible, code-driven explanatory animation and supporting vector graphics; no interactive, 3Blue1Brown-specific, or OpenGL-only requirement was stated.

## Verified system facts from the repository

- RYTT maps language to 26 primitive geometric glyphs plus 23 compound chord ligatures. It uses lowercase **Ground Plane** tokens at `Z=0`, PUA `E000–E019` for primitives, and uppercase **Elevated Plane** tokens at `Z=25`, PUA `E800–E819` for primitives.
- The compiler applies a greedy, longest-match ligature scan. The named system seal `RYTT` is a four-letter chord; the sample vocabulary includes multi-letter chords such as `THE`, `ING`, and `ER`.
- Exact reversibility is represented by `D(C(S)) ≡ S`. The README identifies Lean 4 proofs for primitive and compound roundtrips.
- The README presents `Tyger Tyger, burning bright,` as its worked example. Direct execution of the repository compiler verifies that the exact 28-character string tokenizes to 24 tokens (`T | y | g | er | SPACE | T | y | g | er | , | SPACE | b | u | r | n | ing | SPACE | b | r | i | g | h | t | ,`) and roundtrips exactly. The visual suite uses this source-verified result.
- The existing README openly distinguishes its token-count metric from comparison to production BPE tokenizers. New visual material will not imply BPE compression superiority.

## Visual identity to preserve

| Element | Treatment |
|---|---|
| Background | Near-black ink/navy field, typically `#06080f` |
| Ground plane | Cyan `#00e5ff`, sparse dotted guides, cool glow |
| Elevated plane / seal | Antique gold `#c8a04e` / warm highlight `#e8c87c` |
| Main text | Parchment `#f5ecd7`; restrained sans/serif pairing |
| Structural language | Fine gold borders, concentric rings, rectangular glyph cells, low-opacity grids |
| Motion language | Deliberate geometric assembly, radial convergence, dual-plane elevation, reversible return |

## Recommended deliverables

1. A README hero loop that introduces the system through a radial glyph field and `RYTT` seal.
2. A concise system explainer animation showing plain text → greedy chord selection → dual-plane placement → exact reverse recovery.
3. Static high-resolution keyframes / graphic plates generated from the animation scenes for direct README use.
4. README embed snippets and a visual asset inventory.

## Source files reviewed

- `README.md`
- `src/rytt/compiler.py`
- `assets/social_preview.svg`
- `assets/pipeline_diagram.svg`

## User-facing factual safety

Present formal verification and repository-local benchmark results exactly as described. Do not make claims of external peer review, independent validation, or superior BPE compression.
