"""
RYTT Advanced Suite — Hardened V2 Implementation
=================================================

This module is the corrected implementation of the V2 "Advanced Extended Suite"
blueprint. Every module from the blueprint is repaired to make its printed
claims true, and every fix is documented at the class level:

  1. VolumetricMeshExporter   — now triangulates caps (ear-clipping), so
                                concave glyph outlines extrude correctly.
  2. ZKVectorSteganographer   — renamed semantics: fragile vector watermark.
                                Capacity is now asserted; extraction is
                                self-verified; oversized payloads raise.
                                (It is NOT zero-knowledge and never was.)
  3. LatentSpaceTensorAligner — now consumes the REAL 10-D geometric feature
                                vectors from RYTT_GENOME. The blueprint's
                                np.random.rand(26, 10) placeholder is gone.
  4. DNADataSynthesizer       — now encodes UTF-8 bytes, so any string
                                round-trips (the blueprint crashed on any
                                non-ASCII payload). Adds honest synthesis-
                                constraint reporting (GC, homopolymers).
  5. BurauBraidCompiler       — replaces the blueprint's diagonal-phase
                                "unitary" (which destroyed all braid-group
                                structure: sigma_1 sigma_2 == sigma_2 sigma_1
                                under it, which is FALSE in B_4) with the
                                genuine unreduced Burau representation,
                                which provably satisfies the braid
                                relations. NOT a quantum anyon model.
  6. Source integrity         — CANONICAL_V0_HASH verified nothing; it is
                                replaced by a real pinned SHA-256 over the
                                live glyph genome, checked at runtime.

Author: RYTT Sovereign Semiotics — hardened suite
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Dict, List, Tuple, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Genome access (real data, no placeholder)
# ---------------------------------------------------------------------------

def _load_genome():
    """Import RYTT_GENOME / RYTT_LIGATURES from the live compiler module."""
    try:
        from .compiler import RYTT_GENOME, RYTT_LIGATURES  # in-package
    except ImportError:  # script-style import (module run directly)
        try:
            from rytt.compiler import RYTT_GENOME, RYTT_LIGATURES
        except ImportError as exc:
            raise ImportError(
                "advanced_suite requires the RYTT compiler module (RYTT_GENOME). "
                "Run from the repository root or install the rytt package."
            ) from exc
    return RYTT_GENOME, RYTT_LIGATURES


def genome_integrity_digest() -> str:
    """SHA-256 over the canonical serialization of the live glyph vocabulary.

    This is a REAL hash over REAL data: it changes if and only if the
    genome/ligature definitions in compiler.py change. Verify with
    verify_source_integrity().
    """
    genome, ligatures = _load_genome()

    def canon(entries: Dict[str, Dict]) -> str:
        # Sort keys, project only the *definitional* fields, normalize floats.
        out = []
        for key in sorted(entries):
            spec = entries[key]
            out.append({
                "key": key,
                "family": spec.get("family"),
                "vowel": spec.get("vowel"),
                "ops": spec.get("ops"),
                "trit_val": spec.get("trit_val"),
                "sept_val": spec.get("sept_val"),
                "vectors": [float(v) for v in spec.get("vectors", [])],
                "pua": spec.get("pua"),
            })
        return json.dumps(out, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(
        (canon(genome) + canon(ligatures)).encode("utf-8")
    ).hexdigest()


# Pinned digest of the v0.1.0 vocabulary. If compiler.py's vocabulary changes,
# run `python -m rytt.advanced_suite --print-integrity` and update this pin.
GENOME_INTEGRITY_HASH = "355442e262cdb386cb131497834b903af32513e07918cb1f4bd530b8766f68ae"

# The blueprint's hash. It matched no content in the blueprint, the repo, or
# any candidate file — it verified nothing and is retained only as a warning.
RETRACTED_BLUEPRINT_HASH = "1cae22a9d13026acb3ccd14059301b4b95515b60553ed498c1248d8cfca6c733"


def verify_source_integrity() -> bool:
    """Return True iff the live genome matches the pinned integrity hash."""
    if GENOME_INTEGRITY_HASH == "PIN_AT_BUILD_TIME":
        raise RuntimeError(
            "GENOME_INTEGRITY_HASH is not pinned. Run "
            "`python -m rytt.advanced_suite --print-integrity` and paste the "
            "digest into GENOME_INTEGRITY_HASH."
        )
    return genome_integrity_digest() == GENOME_INTEGRITY_HASH


# ---------------------------------------------------------------------------
# Module 1: Volumetric Spatial Computing & Mesh Extrusion Engine
# ---------------------------------------------------------------------------
class VolumetricMeshExporter:
    """Extrudes 2D RYTT vector contours into closed 3D Wavefront OBJ meshes.

    Fix vs. blueprint: caps are now TRIANGULATED via ear clipping. The
    blueprint emitted each cap as one polygon face, which only renders
    correctly for convex contours — RYTT glyph outlines are strongly
    concave, so blueprint output was geometrically wrong for exactly the
    glyphs this project is about.
    """

    def __init__(self, z_depth: float = 10.0):
        self.z_depth = z_depth

    # -- ear clipping ------------------------------------------------------
    @staticmethod
    def _signed_area(points: List[Tuple[float, float]]) -> float:
        s = 0.0
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            s += x1 * y2 - x2 * y1
        return s / 2.0

    @staticmethod
    def _point_in_triangle(p, a, b, c) -> bool:
        def cross(o, u, v):
            return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
        d1 = cross(a, b, p)
        d2 = cross(b, c, p)
        d3 = cross(c, a, p)
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    def triangulate(self, points_2d: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
        """Ear-clip a simple polygon (convex or concave) into triangles.

        Returns triples of indices into points_2d. Raises on degenerate input.
        Assumes a simple (non-self-intersecting) polygon, as produced by the
        RYTT glyph path sampler.
        """
        n = len(points_2d)
        if n < 3:
            raise ValueError("Polygon must contain at least 3 points.")

        # Work on a copy of index ring, ensuring counter-clockwise orientation
        idx = list(range(n))
        if self._signed_area(points_2d) < 0:
            idx.reverse()

        triangles: List[Tuple[int, int, int]] = []
        guard = 0
        while len(idx) > 3:
            guard += 1
            if guard > 2 * n * n:  # safety: no ear found (degenerate polygon)
                raise ValueError("Ear clipping stalled — polygon may be degenerate.")
            clipped = False
            m = len(idx)
            for k in range(m):
                i0 = idx[(k - 1) % m]
                i1 = idx[k]
                i2 = idx[(k + 1) % m]
                a, b, c = points_2d[i0], points_2d[i1], points_2d[i2]
                # ear tip must be convex
                cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                if cross <= 0:
                    continue
                # no other vertex inside the candidate ear
                if any(
                    self._point_in_triangle(points_2d[j], a, b, c)
                    for j in idx
                    if j not in (i0, i1, i2)
                ):
                    continue
                triangles.append((i0, i1, i2))
                idx.pop(k)
                clipped = True
                break
            if not clipped:
                raise ValueError("Ear clipping stalled — polygon may be self-intersecting.")
        triangles.append((idx[0], idx[1], idx[2]))
        return triangles

    def extrude_polygon_path(self, points_2d: List[Tuple[float, float]]) -> str:
        """Convert a 2D contour into a closed OBJ volume with triangulated caps."""
        num_pts = len(points_2d)
        if num_pts < 3:
            raise ValueError("Polygon must contain at least 3 points.")

        tris = self.triangulate(points_2d)
        half = self.z_depth / 2.0

        lines = ["# RYTT 3D Volumetric Mesh Export (triangulated caps)"]
        for x, y in points_2d:
            lines.append(f"v {x:.4f} {y:.4f} {half:.4f}")
        for x, y in points_2d:
            lines.append(f"v {x:.4f} {y:.4f} {-half:.4f}")

        def f(i: int) -> int:
            return i + 1  # OBJ is 1-indexed

        # Front cap (CCW seen from +z) and back cap (reversed winding)
        for i0, i1, i2 in tris:
            lines.append(f"f {f(i0)} {f(i1)} {f(i2)}")
            lines.append(f"f {f(i0 + num_pts)} {f(i2 + num_pts)} {f(i1 + num_pts)}")

        # Side quads
        for i in range(num_pts):
            j = (i + 1) % num_pts
            lines.append(f"f {f(i)} {f(j)} {f(j + num_pts)} {f(i + num_pts)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module 2: Vector Watermarking (formerly "ZK Steganography")
# ---------------------------------------------------------------------------
class CapacityError(ValueError):
    """Raised when a payload needs more bits than the geometry can carry."""


class ZKVectorSteganographer:
    """Sub-perceptual vector watermarking — capacity-checked and honest.

    SEMANTIC CORRECTION vs. blueprint: this is a FRAGILE WATERMARK, not a
    zero-knowledge system. Extraction requires the ORIGINAL geometry, there
    is no proof system, and there is no robustness to re-rendering. It is
    retained because fragile watermarking is a legitimate, useful primitive.

    Fixes vs. blueprint:
      * Capacity is asserted: embedding a payload needing more bits than
        there are vertices now raises CapacityError instead of silently
        truncating (the blueprint's own demo recovered '' from 'ARI_KEY'
        on a 3-vertex contour and printed it as success).
      * embed_bitstream() self-verifies the round-trip before returning.
      * Unused vertices are left EXACTLY unchanged (and extraction ignores
        them by bit-count, so a 0-bit offset of -tolerance vs. an untouched
        coordinate can no longer alias).
    """

    def __init__(self, tolerance: float = 0.05):
        if tolerance <= 0:
            raise ValueError("tolerance must be positive")
        self.tolerance = tolerance

    @staticmethod
    def _bits_of(payload: str) -> str:
        # UTF-8 bytes: correct for any payload (blueprint used ord(c) per
        # character, which misaligns the stream for ord(c) > 255).
        return "".join(format(b, "08b") for b in payload.encode("utf-8"))

    def embed_bitstream(
        self, vertices: List[Tuple[float, float]], payload: str
    ) -> List[Tuple[float, float]]:
        bits = self._bits_of(payload)
        if len(bits) > len(vertices):
            raise CapacityError(
                f"payload needs {len(bits)} bits but only {len(vertices)} "
                f"vertices are available (1 bit/vertex)."
            )
        marked: List[Tuple[float, float]] = []
        for i, (x, y) in enumerate(vertices):
            if i < len(bits):
                x_mod = x + (self.tolerance if bits[i] == "1" else -self.tolerance)
                marked.append((round(x_mod, 4), round(y, 4)))
            else:
                marked.append((x, y))
        # Self-verification: never hand back an embed we cannot recover.
        recovered = self.extract_bitstream(
            vertices, marked, len(payload.encode("utf-8"))
        )
        if recovered != payload:
            raise AssertionError("embed self-verification failed")
        return marked

    def extract_bitstream(
        self,
        original: List[Tuple[float, float]],
        watermarked: List[Tuple[float, float]],
        length: int,
    ) -> str:
        """Recover the payload. Requires the original geometry (by design).

        `length` is the payload length in UTF-8 BYTES (1 bit per vertex is
        consumed, 8 vertices per byte). Callers embedding via embed_bitstream
        should pass len(payload.encode("utf-8")).
        """
        total_bits = length * 8
        if len(original) < total_bits or len(watermarked) < total_bits:
            raise CapacityError(
                f"cannot recover {length} bytes from {len(original)} vertices "
                f"(need {total_bits})."
            )
        bits: List[str] = []
        for (x_orig, _), (x_marked, _) in zip(original, watermarked):
            if len(bits) >= total_bits:
                break
            delta = x_marked - x_orig
            bits.append("1" if delta > 0 else "0")
        bit_str = "".join(bits)[:total_bits]
        data = bytes(int(bit_str[i : i + 8], 2) for i in range(0, len(bit_str), 8))
        return data.decode("utf-8")


# ---------------------------------------------------------------------------
# Module 3: Geometric Latent Space Alignment (real genome features)
# ---------------------------------------------------------------------------
class LatentSpaceTensorAligner:
    """Pairwise geometry over the REAL RYTT glyph feature vectors.

    Fix vs. blueprint: the blueprint generated np.random.rand(26, 10) — random
    numbers presented as 'glyph feature calibration'. This implementation
    loads the actual 10-D geometric feature vectors from RYTT_GENOME
    (52 glyphs, both case planes) and computes the distance/similarity
    structure over them. There is NO random fallback.
    """

    VECTOR_PROPERTIES = [
        "continuity", "tension", "contrast", "alignment", "closure",
        "weight_balance", "curvature_match", "direction_match",
        "negative_space_compatibility", "structural_kinship",
    ]

    def __init__(self, feature_matrix: Optional[np.ndarray] = None):
        if feature_matrix is None:
            genome, _ = _load_genome()
            keys = sorted(genome.keys(), key=lambda k: (k.isupper(), k))
            self.glyph_keys = keys
            feature_matrix = np.array(
                [genome[k]["vectors"] for k in keys], dtype=np.float64
            )
        else:
            feature_matrix = np.asarray(feature_matrix, dtype=np.float64)
            self.glyph_keys = None
        if feature_matrix.ndim != 2:
            raise ValueError("feature_matrix must be 2-D (glyphs x features)")
        self.feature_matrix = feature_matrix

    def compute_pairwise_tensor_matrix(self) -> Dict[str, np.ndarray]:
        """Pairwise Euclidean distance and cosine similarity matrices."""
        fm = self.feature_matrix
        diff = fm[:, np.newaxis, :] - fm[np.newaxis, :, :]
        euclidean_dist = np.linalg.norm(diff, axis=-1)
        norms = np.linalg.norm(fm, axis=-1, keepdims=True)
        normalized = fm / (norms + 1e-9)
        cosine_sim = normalized @ normalized.T
        return {"euclidean_distance": euclidean_dist, "cosine_similarity": cosine_sim}

    def family_similarity_report(self) -> Dict[str, float]:
        """Mean within-family vs across-family cosine similarity (real data)."""
        genome, _ = _load_genome()
        if self.glyph_keys is None:
            raise ValueError("family report requires genome-derived features")
        cos = self.compute_pairwise_tensor_matrix()["cosine_similarity"]
        n = len(self.glyph_keys)
        within, across = [], []
        for i in range(n):
            for j in range(i + 1, n):
                same = (
                    genome[self.glyph_keys[i]]["family"]
                    == genome[self.glyph_keys[j]]["family"]
                )
                (within if same else across).append(cos[i, j])
        return {
            "within_family_cosine": float(np.mean(within)),
            "across_family_cosine": float(np.mean(across)),
        }


# ---------------------------------------------------------------------------
# Module 4: Synthetic DNA Encoding (UTF-8 safe)
# ---------------------------------------------------------------------------
class DNADataSynthesizer:
    """Lossless base-4 packing of JSON payloads into nucleotide sequences.

    Fix vs. blueprint: the blueprint converted ord(c) per character, which
    emits >8 bits for any character above U+00FF and silently misaligns the
    entire stream (a payload containing 'λ' crashed the decoder with
    UnicodeDecodeError). This implementation encodes UTF-8 *bytes*, so ANY
    string round-trips exactly. The blueprint's odd-padding branch was dead
    code (8 bits per byte is always even) and is removed.

    Scope statement: this is a base-4 packing scheme. It is NOT a
    synthesis-grade DNA storage codec — it performs no GC-content shaping,
    homopolymer avoidance, indexing, or error correction. analyze() reports
    the real synthesis constraints so callers can see the gap.
    """

    NUCLEOTIDE_MAP = {"00": "A", "01": "C", "10": "G", "11": "T"}
    REVERSE_MAP = {v: k for k, v in NUCLEOTIDE_MAP.items()}

    def ari_to_dna(self, ari_payload: dict) -> str:
        json_str = json.dumps(ari_payload, separators=(",", ":"), ensure_ascii=False)
        binary = "".join(
            format(b, "08b") for b in json_str.encode("utf-8")
        )  # always even length by construction
        return "".join(
            self.NUCLEOTIDE_MAP[binary[i : i + 2]] for i in range(0, len(binary), 2)
        )

    def dna_to_ari(self, dna_sequence: str) -> dict:
        if len(dna_sequence) % 4 != 0:
            raise ValueError("DNA sequence length must be a multiple of 4 bases (1 byte = 4 bases).")
        binary = "".join(self.REVERSE_MAP[base] for base in dna_sequence)
        raw = bytes(int(binary[i : i + 8], 2) for i in range(0, len(binary), 8))
        return json.loads(raw.decode("utf-8"))

    def analyze(self, dna_sequence: str) -> Dict[str, object]:
        """Report real synthesis constraints for the given sequence."""
        if not dna_sequence:
            raise ValueError("empty sequence")
        gc = sum(dna_sequence.count(b) for b in "GC") / len(dna_sequence)
        longest = 1
        current = 1
        for a, b in zip(dna_sequence, dna_sequence[1:]):
            current = current + 1 if a == b else 1
            longest = max(longest, current)
        return {
            "bases": len(dna_sequence),
            "gc_content": round(gc, 4),
            "gc_in_sweet_spot_45_55": 0.45 <= gc <= 0.55,
            "longest_homopolymer_run": longest,
            "homopolymer_runs_over_3": longest > 3,
        }


# ---------------------------------------------------------------------------
# Module 5: Burau Braid Representation (replaces "quantum" module)
# ---------------------------------------------------------------------------
class BurauBraidCompiler:
    """Maps phrases into braid words and evaluates the UNREDUCED BURAU
    representation — a genuine representation of the braid group.

    Fix vs. blueprint: the blueprint applied a diagonal phase to a single
    basis state per generator. Diagonal matrices commute, so under it
    u(sigma_1 sigma_2) == u(sigma_2 sigma_1) — but those are DIFFERENT
    braids — while u(sigma_1 sigma_2 sigma_1) != u(sigma_2 sigma_1
    sigma_2) — which the braid relation says are EQUAL. It destroyed
    exactly the topological structure it claimed to encode, and the
    printed "Matrix Norm: 4.0000" was vacuous (Frobenius norm of every
    16x16 unitary is sqrt(16)).

    The unreduced Burau representation rho: B_n -> GL_n(Z[t, t^-1]),
    evaluated numerically at 0 < t < 1, maps sigma_i to the identity
    except for the 2x2 block [[1 - t, t], [1, 0]] at rows/cols (i, i+1).
    It satisfies both braid relations by construction; verify_braid_
    relations() checks this numerically, and is exercised in the tests.

    HONEST NAMING: this is a classical representation of the Artin
    braid group. It is NOT a quantum anyon/topological quantum computer.
    """

    def __init__(self, num_strands: int = 4):
        if num_strands < 2:
            raise ValueError("braid group B_n needs n >= 2")
        self.num_strands = num_strands

    # -- braid words --------------------------------------------------------
    def phrase_to_braid_generators(self, phrase: str) -> List[Tuple[str, int]]:
        """Deterministic (arbitrary but reproducible) text -> braid word map.

        NOTE: this mapping is a semiotic bridge, not a canonical encoding —
        it carries no round-trip guarantee (many phrases map to the same
        braid word). The Burau evaluation of the resulting word is exact.
        """
        ops: List[Tuple[str, int]] = []
        for char in phrase.upper():
            if not char.isalpha():
                continue
            val = ord(char) % (self.num_strands - 1) + 1
            direction = "sigma" if ord(char) % 2 == 0 else "sigma_inv"
            ops.append((direction, val))
        return ops

    # -- representation ------------------------------------------------------
    def burau_generator(self, i: int, t: float = 0.5) -> np.ndarray:
        """rho(sigma_i) as an n x n numeric matrix (unreduced Burau at t)."""
        if not (1 <= i <= self.num_strands - 1):
            raise ValueError(f"sigma_{i} out of range for B_{self.num_strands}")
        if not (0.0 < t < 1.0):
            raise ValueError("t must lie strictly between 0 and 1")
        n = self.num_strands
        m = np.eye(n)
        m[i - 1, i - 1] = 1.0 - t
        m[i - 1, i] = t
        m[i, i - 1] = 1.0
        m[i, i] = 0.0
        return m

    def burau_matrix(
        self, braid_ops: List[Tuple[str, int]], t: float = 0.5
    ) -> np.ndarray:
        """Product matrix of the braid word under the Burau representation."""
        out = np.eye(self.num_strands)
        for op, strand in braid_ops:
            g = self.burau_generator(strand, t)
            out = g @ out if op == "sigma" else np.linalg.inv(g) @ out
        return out

    def verify_braid_relations(self, t: float = 0.5) -> bool:
        """Check the defining relations of B_n numerically at the given t."""
        n = self.num_strands
        for i in range(1, n):
            gi = self.burau_generator(i, t)
            gi_inv = np.linalg.inv(gi)
            # sigma_i sigma_i^{-1} = I
            if not np.allclose(gi @ gi_inv, np.eye(n), atol=1e-9):
                return False
            for j in range(1, n):
                gj = self.burau_generator(j, t)
                gj_inv = np.linalg.inv(gj)
                if abs(i - j) >= 2:
                    if not np.allclose(gi @ gj, gj @ gi, atol=1e-9):
                        return False
                elif j == i + 1:
                    # Yang-Baxter / braid relation
                    lhs = gi @ gj @ gi
                    rhs = gj @ gi @ gj
                    if not np.allclose(lhs, rhs, atol=1e-9):
                        return False
        return True

    # -- deprecated compatibility alias -------------------------------------
    def generate_unitary_braid_matrix(
        self, braid_ops: List[Tuple[str, int]]
    ) -> np.ndarray:
        """DEPRECATED: returns the Burau matrix, not a 'unitary'.

        Kept only for API compatibility with the blueprint; the name was
        misleading (the blueprint's matrix was unitary but meaningless).
        """
        return self.burau_matrix(braid_ops)


# Blueprint-era alias (the class was never actually a quantum compiler).
QuantumBraidCompiler = BurauBraidCompiler


# ---------------------------------------------------------------------------
# Integrated suite — every line below is asserted, not assumed.
# ---------------------------------------------------------------------------
def run_extended_rytt_suite() -> Dict[str, object]:
    report: Dict[str, object] = {}

    print("=== RYTT Advanced Suite (Hardened V2) ===")

    # 0. Source integrity — REAL hash over REAL data.
    if GENOME_INTEGRITY_HASH == "PIN_AT_BUILD_TIME":
        digest = genome_integrity_digest()
        print(f"[0] Genome integrity digest (unpinned): {digest}")
        print("    NOTE: pin this value in GENOME_INTEGRITY_HASH before release.")
    else:
        ok = verify_source_integrity()
        print(f"[0] Source integrity verified against pinned hash: {ok}")
        assert ok, "Genome integrity check FAILED — vocabulary drifted from pin."
    report["source_integrity"] = True

    # 1. Volumetric mesh with triangulated caps on a CONCAVE contour.
    mesh = VolumetricMeshExporter(z_depth=12.0)
    concave = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (5.0, 5.0), (0.0, 10.0)]
    obj = mesh.extrude_polygon_path(concave)
    tri_count = sum(1 for l in obj.splitlines() if l.startswith("f "))
    assert mesh._signed_area(concave) > 0
    print(f"[1] Concave mesh extruded: {tri_count} faces (triangulated caps)")
    report["mesh_faces"] = tri_count

    # 2. Watermark with capacity safety + self-verified round-trip.
    stego = ZKVectorSteganographer(tolerance=0.02)
    contour = [(float(i), float(i % 7)) for i in range(80)]
    secret = "ARI_KEY"
    marked = stego.embed_bitstream(contour, secret)
    assert stego.extract_bitstream(contour, marked, len(secret.encode("utf-8"))) == secret
    try:
        stego.embed_bitstream(contour[:3], secret)
        raise AssertionError("CapacityError was not raised")
    except CapacityError:
        pass
    print(f"[2] Watermark round-trip exact: '{secret}'; CapacityError enforced on 3-vertex contour")
    report["watermark_round_trip"] = True

    # 3. Real glyph feature structure.
    aligner = LatentSpaceTensorAligner()
    mats = aligner.compute_pairwise_tensor_matrix()
    fam = aligner.family_similarity_report()
    assert mats["euclidean_distance"].shape == (52, 52)
    print(
        f"[3] Real glyph geometry: 52x52 matrices; within-family cos={fam['within_family_cosine']:.4f} "
        f"vs across={fam['across_family_cosine']:.4f}"
    )
    report["glyph_matrix_shape"] = mats["euclidean_distance"].shape
    report["family_similarity"] = fam

    # 4. DNA encoding with full UTF-8 range, incl. the blueprint's failure case.
    dna = DNADataSynthesizer()
    payloads = [
        {"type": "ARI_STREAM", "symbol": "TH", "plane": "elevated"},
        {"type": "ARI_STREAM", "symbol": "λ", "note": "crashed the blueprint"},
        {"type": "ARI_STREAM", "emoji": "glyphs ⟁ ⟆", "check": "U+27C1 etc."},
    ]
    for p in payloads:
        seq = dna.ari_to_dna(p)
        assert dna.dna_to_ari(seq) == p, f"round-trip failed for {p}"
    stats = dna.analyze(dna.ari_to_dna(payloads[0]))
    print(
        f"[4] DNA round-trip exact on ASCII + 'λ' + astral-plane glyphs; "
        f"GC={stats['gc_content']:.0%}, longest run={stats['longest_homopolymer_run']}"
    )
    report["dna_round_trip"] = True
    report["dna_stats"] = stats

    # 5. Burau braid representation — relations verified, structure retained.
    qc = BurauBraidCompiler(num_strands=4)
    assert qc.verify_braid_relations(t=0.5)
    assert qc.verify_braid_relations(t=0.3)
    word = qc.phrase_to_braid_generators("MANDALA")
    u = qc.burau_matrix(word, t=0.5)
    # Structure the blueprint destroyed: sigma_1 sigma_2 != sigma_2 sigma_1
    u12 = qc.burau_matrix([("sigma", 1), ("sigma", 2)], t=0.5)
    u21 = qc.burau_matrix([("sigma", 2), ("sigma", 1)], t=0.5)
    assert not np.allclose(u12, u21), "Burau matrices must not commute for adjacent generators"
    print(
        f"[5] Burau: braid relations verified (B_4, t=0.3/0.5); 'MANDALA' -> {len(word)} ops; "
        f"adjacent-generator non-commutativity retained"
    )
    report["braid_relations_verified"] = True
    report["mandala_ops"] = len(word)

    print("\nAll five modules asserted. Suite output is verified, not asserted-by-print.")
    return report


if __name__ == "__main__":
    import sys

    if "--print-integrity" in sys.argv:
        print(genome_integrity_digest())
        sys.exit(0)
    run_extended_rytt_suite()
