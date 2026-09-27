# RYTT Advanced Suite (Hardened V2) — Corrections & Evidence

This document records, fix by fix, what was wrong in the V2 "Advanced Extended
Suite" blueprint, what was changed, and the measured evidence that each
correction holds. Every claim below was verified by an executable test in
`tests/test_advanced_suite.py` (26 tests, all passing) and by live assertions
in `run_extended_rytt_suite()`.

---

## 0. Source hash "verification" verified nothing — replaced

**Blueprint:** a constant `CANONICAL_V0_HASH` was printed at the top of every
run. No code ever computed a hash or compared it to anything; the constant
matched no content in the blueprint, the repository, or any obvious candidate
file. It was a decorative badge.

**Fix:** `genome_integrity_digest()` computes a real SHA-256 over the
canonical serialization of the live `RYTT_GENOME` + `RYTT_LIGATURES`
definitions; the value is pinned in `GENOME_INTEGRITY_HASH` and
`verify_source_integrity()` compares live vs. pin on every suite run.
Vocabulary drift in `compiler.py` now fails loudly.

---

## 1. Mesh extrusion: single-face caps → ear-clipped triangles

**Blueprint bug:** each cap was emitted as ONE polygon face. That only renders
as a filled surface for convex contours. RYTT glyph outlines are strongly
concave — the blueprint output was geometrically wrong for exactly the glyphs
this project exists to represent.

**Fix:** `triangulate()` implements ear clipping; caps are triangulated,
sides remain quads. Correctness is asserted by comparing summed triangle area
to the polygon's shoelace area (test: `test_concave_polygon_triangulated`).

---

## 2. "Zero-Knowledge" steganography → capacity-checked fragile watermark

**Blueprint bugs, all demonstrated live:**

- The blueprint's own demo embedded `'ARI_KEY'` (56 bits) into a 3-vertex
  contour (3-bit capacity), silently recovered `''`, and printed the line as
  if it had succeeded.
- Oversized payloads truncated silently with no error.
- It is not zero-knowledge in any sense: extraction requires the original
  geometry; there is no proof system.

**Fix:** `CapacityError` on insufficient capacity; `embed_bitstream()` runs a
full extract-and-compare self-verification before returning; `length` is
unambiguously measured in UTF-8 bytes; the class docstring states plainly
that this is a fragile watermark. A legitimate, useful primitive — once it
stops calling itself something it isn't.

---

## 3. "Neuromorphic" aligner: `np.random.rand` → real glyph vectors

**Blueprint bug:** the "10-D Visual Interval tensor latent space calibration"
generated `np.random.rand(26, 10)` with a fixed seed and computed similarity
matrices over random noise. The glyphs' real 10-dimensional feature vectors
already exist in `RYTT_GENOME` — the blueprint simply ignored them.

**Fix:** `LatentSpaceTensorAligner` loads the real vectors for all 52 glyphs
(both case planes) with no random fallback, and adds
`family_similarity_report()`. Measured structure over the real data:
within-family mean cosine similarity **0.9158** vs. across-family **0.7660**
— the glyph families are genuinely separated in feature space.

---

## 4. DNA encoding: crashed on non-ASCII → UTF-8-safe, with honest scope

**Blueprint bug, demonstrated live:** `format(ord(c), '08b')` emits 10+ bits
for any character above U+00FF, misaligning the entire bitstream. A payload
containing `λ` crashed the decoder with `UnicodeDecodeError`. (The blueprint's
own demo only "passed" because `json.dumps` escapes non-ASCII before the
encoder ever sees it.) The odd-length padding branch was dead code — 8 bits
per byte is always even.

**Fix:** encode UTF-8 **bytes**; any string round-trips exactly (tests cover
ASCII, `λ`, and astral-plane glyphs `⟁⟆`). `analyze()` now reports real
synthesis constraints (GC content, homopolymer runs), and the docstring states
plainly that this is base-4 packing — NOT a synthesis-grade storage codec.

---

## 5. "Quantum braid" matrix: destroyed braid structure → genuine Burau representation

**Blueprint bug, demonstrated live:** the generator was a diagonal phase on a
single basis state. Diagonal matrices commute, so under the blueprint
`u(σ₁σ₂) == u(σ₂σ₁)` — **but those are different braids** — while
`u(σ₁σ₂σ₁) ≠ u(σ₂σ₁σ₂)` — **but the braid relation says those words are
equal**. The construction inverted the braid group's actual structure. The
printed "Unitary Matrix Norm: 4.0000" was vacuous: it is `√dim`, the Frobenius
norm of *every* 16×16 unitary.

**Fix:** `BurauBraidCompiler` implements the unreduced Burau representation
ρ: B_n → GL_n, σᵢ ↦ identity except the 2×2 block `[[1−t, t], [1, 0]]`.
Verified numerically (test: `test_braid_relations_hold`) for B₃–B₅ at
t ∈ {0.2, 0.5, 0.8}: braid relations hold, adjacent generators do not
commute, distant generators do, inverses annihilate, and
u(σ₁σ₂σ₁) == u(σ₂σ₁σ₂) as the Yang–Baxter/braid relation demands.

**Honest naming:** this is a classical representation of the Artin braid
group. It is not an anyon model and not topological quantum computing. The
blueprint-era alias `QuantumBraidCompiler` is retained for API compatibility
with a deprecation note.

---

## Test evidence

```
$ pytest tests/test_advanced_suite.py -v
26 passed

$ python -m rytt.advanced_suite
[0] Source integrity verified against pinned hash: True
[1] Concave mesh extruded: 11 faces (triangulated caps)
[2] Watermark round-trip exact: 'ARI_KEY'; CapacityError enforced on 3-vertex contour
[3] Real glyph geometry: 52x52 matrices; within-family cos=0.9158 vs across=0.7660
[4] DNA round-trip exact on ASCII + 'λ' + astral-plane glyphs; GC=59%, longest run=3
[5] Burau: braid relations verified (B_4, t=0.3/0.5); adjacent-generator
    non-commutativity retained
```

Every printed line above is backed by an assertion that runs before it is
printed. No number in this document is unmeasured.
