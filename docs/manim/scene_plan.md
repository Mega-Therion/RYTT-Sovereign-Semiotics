# RYTT: Geometry That Returns

## Overview

| Field | Specification |
|---|---|
| Topic | A visual introduction to RYTT’s geometric primitives, greedy chord tokenization, dual-plane casing, and exact recovery. |
| Hook | What if a line of language could become geometry without losing a single character? |
| Target audience | Developers, researchers, technical readers, and GitHub visitors; no prior mathematical background required. |
| Estimated length | Approximately 47 seconds, silent and optimized for README, social preview, and loop-friendly playback. |
| Key insight | RYTT’s value is the reversible correspondence between source text and a dual-plane geometric token stream—not a claim of universal BPE compression. |
| Framework | ManimCE. No plugins required. |
| Narration | None. Typography, rhythm, and visual emphasis carry the explanation. |

## Narrative Arc

The piece begins with an elegant radial field of RYTT primitives and a central seal, establishing the system as a geometric visual language. It then makes the system concrete by compiling the README’s `Tyger Tyger, burning bright,` example into primitive and chord tokens. A spatial elevation reveal explains that case is preserved through a dual-plane coordinate system. The ending closes the loop with the involution `D(C(S)) ≡ S`, returning the glyph stream to exactly the original text.

---

## Scene 1: The Radial Lexicon

**Duration**: 9 seconds  
**Purpose**: Establish the RYTT identity and show that its alphabet is a field of geometric primitives.

### Visual Elements

- Low-opacity concentric rings and fine radial ticks on a near-black ink background.
- A 26-position radial field of atomic glyph primitives, alternating cyan and antique-gold emphasis based on symmetry treatment.
- Central `RYTT` seal, rendered as a ring with intersecting T-structure and crossbar.
- Title lockup: `RYTT SOVEREIGN SEMIOTICS` and `RADIAL YETT–TOPOLOGY TOKENIZATION`.

### Content

The radial guide resolves first, then glyphs draw themselves around the circumference in a clockwise sequence. The center seal flashes alive, while the title arrives in restrained parchment typography. The final beat holds a subtle pulse to create a clean hero keyframe.

### Technical Notes

- Manim core only: `Circle`, `Line`, `VGroup`, `Create`, `LaggedStart`, and `Text`.
- No external assets and no plugins.
- The last second preserves the visual composition for static hero capture.

---

## Scene 2: The Chord Compiler

**Duration**: 17 seconds  
**Purpose**: Demonstrate greedy longest-match tokenization using the repository’s Blake example.

### Visual Elements

- Source text: `Tyger Tyger, burning bright,` in parchment.
- A scanner line that travels left-to-right across the string.
- Chord brackets that visibly select `ER` and `ING` as compound ligatures.
- A lower token rail where primitive glyphs and chord glyphs appear as individual cyan/gold cells.
- Source character count and output RYTT token count, with an explicit exact-recovery label.

### Content

The source line appears as ordinary text. The scanner examines it left to right; when it reaches lowercase `er` and `ing`, the characters collapse into single geometric chord cells. Remaining characters resolve into primitive glyphs. The token rail finishes as a compact symbolic composition, with the source-verified text `28 source characters → 24 RYTT tokens` and `exact text recovery` shown separately to avoid a BPE-compression claim.

### Technical Notes

- Manim core only: `Text`, `RoundedRectangle`, `Line`, `Arrow`, `Transform`, `FadeIn`, `FadeOut`.
- Use geometric approximations for the displayed `T`, `Y`, `G`, `ER`, `B`, `U`, `R`, `N`, `ING`, `I`, `H` primitives/chords.
- Keep source and output legible at 1080p. The final token rail acts as an infographic keyframe.

---

## Scene 3: Case Becomes a Coordinate

**Duration**: 12 seconds  
**Purpose**: Make the Ground/Elevated plane convention immediately intuitive.

### Visual Elements

- A pseudo-3D isometric stack with a cyan Ground Plane at `Z = 0` and an antique-gold Elevated Plane at `Z = 25`.
- A matched lowercase / uppercase `T` glyph pair, with the gold glyph rising from the cyan plane.
- PUA marker chips: `E000–E019` and `E800–E819`.
- Vertical guide line and a clearly labelled `case as spatial coordinate` statement.

### Content

A cyan `t` glyph activates on the Ground Plane. Its uppercase counterpart rises vertically to the Elevated Plane, changing color while retaining the same geometric family. The coordinate labels and PUA ranges resolve, followed by a short statement that both planes are disjoint and preserve casing without auxiliary metadata.

### Technical Notes

- Manim core only; no `ThreeDScene` is needed. Use 2D parallelograms and vertical connectors for reliable README-friendly pseudo-3D.
- Core palette semantic: cyan denotes Ground/lowercase; gold denotes Elevated/uppercase.

---

## Scene 4: The Lossless Return

**Duration**: 9 seconds  
**Purpose**: Close the explanatory loop and foreground the repository’s reversibility guarantee.

### Visual Elements

- The encoded glyph/token stream from Scene 2, condensed to a luminous central path.
- A forward label `C(S)` and a return label `D(·)`.
- An exact-recovery equation: `D(C(S)) ≡ S`.
- A cyan circular return path that transforms back into the original `Tyger Tyger, burning bright,` line.
- Footer: `exact roundtrip · Lean 4 proofs in repository`.

### Content

The glyph stream is drawn into a closed loop around the central equation. A return vector triggers, and the symbols reconstitute into exactly the same source line shown in Scene 2. The proof equation and verification statement hold in the final frame, providing a natural README end card.

### Technical Notes

- Manim core only. Use `Text` instead of `MathTex`; no TeX installation is required.
- Use `TransformMatchingShapes` only when the glyph groups have compatible geometry; otherwise crossfade cleanly.
- End on an uncluttered, readable poster frame.

---

## Transitions and Flow

A thin gold radial motif carries Scene 1 into the scan line of Scene 2. Scene 2’s token rail tilts into the pseudo-3D planes of Scene 3, while the vertical coordinate line becomes the circular recovery arrow in Scene 4. Every scene resolves to one crisp visual state that can be captured as a standalone README graphic.

## Color Palette

| Role | Color | Use |
|---|---|---|
| Background | `#06080F` | Ink-field background |
| Ground plane | `#00E5FF` | Lowercase, primitive lattice, recovery path |
| Elevated plane | `#C8A04E` | Uppercase, seal, chord emphasis, structural borders |
| Highlight gold | `#E8C87C` | Brighter seal/selected chord highlights |
| Parchment | `#F5ECD7` | Primary reader-facing text |
| Muted ink | `#7A6B50` / `#5A6580` | Captions, construction guides, secondary labels |

## Mathematical and Semantic Content

The visual material is scoped to repository-defined claims: 26 primitives, 23 compound ligatures, greedy longest-match selection, Ground `Z=0` / Elevated `Z=25` case encoding, disjoint PUA ranges, and the reversible mapping `D(C(S)) ≡ S`. The animation does not depict RYTT as outperforming general-purpose BPE compression.

## Implementation Order

1. Build a reusable visual system: colors, background treatment, glyph-drawing helpers, labels, glow layers, and clip-safe layout.
2. Build Scene 2 first because it defines the source-text-to-token visual grammar used in Scene 4.
3. Build Scene 3’s plane composition, then Scene 1’s radial composition.
4. Build Scene 4 using reduced objects from Scene 2, render all scenes at low quality, review, then finalize at 1080p60.

## README Deliverables

| Asset | Source | Intended README use |
|---|---|---|
| `rytt_geometry_that_returns.mp4` | Concatenated four-scene explainer | Linked or embedded animation preview |
| `rytt_hero_loop.gif` | Trimmed Scene 1 loop | Top-of-README animated visual |
| `rytt_scene_1_radial_lexicon.png` | Scene 1 keyframe | Hero/social graphic |
| `rytt_scene_2_chord_compiler.png` | Scene 2 keyframe | Worked-example illustration |
| `rytt_scene_3_dual_plane.png` | Scene 3 keyframe | Case-coordinate explanation |
| `rytt_scene_4_lossless_return.png` | Scene 4 keyframe | Verification/end-card illustration |
| `README_VISUALS.md` | New integration guide | Alt text and copy/paste Markdown snippets |
