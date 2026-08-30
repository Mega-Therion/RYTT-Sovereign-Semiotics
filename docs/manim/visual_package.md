# RYTT README Visual Package

This package provides an original, code-rendered visual suite for **RYTT Sovereign Semiotics**. The assets preserve the repository’s ink-field, cyan Ground Plane, antique-gold Elevated Plane, and geometric-glyph visual language while explaining the repository-defined compiler workflow.

> The explainer uses the source-verified compiler result for `Tyger Tyger, burning bright,`: **28 source characters become 24 RYTT tokens**, and decompilation returns the same source text exactly. This wording intentionally avoids an unsupported comparison with general-purpose BPE tokenizers.

## Asset Inventory

| Asset | Format | README role | Suggested placement |
|---|---|---|---|
| `assets/manim/rytt_radial_lexicon_preview.gif` | Animated GIF, 960×540 | Immediately visible hero motion | Directly below the repository title and badges |
| `assets/manim/rytt_geometry_that_returns.mp4` | Silent MP4, 1920×1080, 1080p60 | Full 36-second visual explainer | Linked from the hero GIF and the System Map section |
| `assets/manim/rytt_scene_1_radial_lexicon.png` | PNG, 1920×1080 | Static hero / social-ready plate | Fallback for low-motion contexts |
| `assets/manim/rytt_scene_2_chord_compiler.png` | PNG, 1920×1080 | Greedy chord-matching worked example | In “From Language to Geometry” |
| `assets/manim/rytt_scene_3_dual_plane.png` | PNG, 1920×1080 | Ground versus Elevated plane explanation | In “Two Planes, One Reversible System” |
| `assets/manim/rytt_scene_4_lossless_cycle.png` | PNG, 1920×1080 | Encode/decode cycle visual | Immediately before the losslessness guarantee |
| `assets/manim/rytt_scene_4_exact_recovery.png` | PNG, 1920×1080 | Exact-recovery end card | In “Why Losslessness Matters” |

## Hero Animation Block

Insert this block directly below the badge row in `README.md`. It links the lightweight GIF preview to the full-resolution silent explainer.

```html
<p align="center">
  <a href="assets/manim/rytt_geometry_that_returns.mp4">
    <img src="assets/manim/rytt_radial_lexicon_preview.gif"
         alt="Animated radial field of RYTT’s geometric glyph primitives. Cyan marks the Ground Plane at Z=0, gold marks the Elevated Plane at Z=25, and the RYTT seal resolves in the center."
         width="100%">
  </a>
</p>

<p align="center">
  <sub><em>Click the animation to open “RYTT: Geometry That Returns,” a silent visual explainer.</em></sub>
</p>
```

## Worked-Example Graphic

Place the following under the “From Language to Geometry” heading, before the existing tokenization table.

```html
<p align="center">
  <img src="assets/manim/rytt_scene_2_chord_compiler.png"
       alt="A RYTT compiler walkthrough. The source text Tyger Tyger, burning bright, is scanned from left to right, with lowercase er and ing selected as geometric chord tokens before remaining characters become primitive glyphs. The graphic states 28 source characters to 24 RYTT tokens and exact source recovery."
       width="100%">
</p>

<p align="center">
  <sub><em>Greedy longest-match selection visibly resolves <code>er</code> and <code>ing</code> before single-letter primitives.</em></sub>
</p>
```

## Dual-Plane Graphic

Place the following after the Ground/Elevated comparison table in “Two Planes, One Reversible System.”

```html
<p align="center">
  <img src="assets/manim/rytt_scene_3_dual_plane.png"
       alt="A pseudo-three-dimensional RYTT dual-plane diagram. A cyan lowercase t occupies the Ground Plane at Z=0 and a gold uppercase T occupies the Elevated Plane at Z=25. The two planes display their separate Unicode Private Use Area ranges."
       width="100%">
</p>

<p align="center">
  <sub><em>Case is represented as a spatial coordinate across disjoint Unicode ranges.</em></sub>
</p>
```

## Lossless-Recovery Graphic

Place this immediately below the equation in “Why Losslessness Matters.”

```html
<p align="center">
  <img src="assets/manim/rytt_scene_4_exact_recovery.png"
       alt="The RYTT lossless-recovery invariant D(C(S)) equals S. A cyan return arc encircles the equation, while the source text Tyger Tyger, burning bright, is shown before and after the transformation to represent exact reconstruction."
       width="100%">
</p>

<p align="center">
  <sub><em>The visual invariant: encode, then reconstruct the exact original source string.</em></sub>
</p>
```

## Optional Full-Explainer Link

If a compact, text-only link is preferred elsewhere in the README, use:

```markdown
[Watch the silent RYTT visual explainer (36 seconds)](assets/manim/rytt_geometry_that_returns.mp4)
```

## Accessibility Notes

Every block includes descriptive alternative text. The GIF is a non-essential enhancement: the static visuals and surrounding explanatory text convey the same system claims, and the full explainer is silent. For motion-sensitive readers, use `rytt_scene_1_radial_lexicon.png` as the hero instead of the GIF.

## Regeneration

The editable Manim source and scene plan are delivered separately with this task as `video.py` and `scenes.md`. The animation contains four independent scenes, in order: `RadialLexicon`, `ChordCompiler`, `DualPlaneCoordinate`, and `LosslessReturn`.
