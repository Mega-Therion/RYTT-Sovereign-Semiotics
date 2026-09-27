"""Property tests for the hardened RYTT Advanced Suite (V2).

Every test asserts behavior, mirroring the repo's invariant-test style.
Run: pytest tests/test_advanced_suite.py -v
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rytt.advanced_suite import (  # noqa: E402
    GENOME_INTEGRITY_HASH,
    BurauBraidCompiler,
    CapacityError,
    DNADataSynthesizer,
    LatentSpaceTensorAligner,
    VolumetricMeshExporter,
    ZKVectorSteganographer,
    genome_integrity_digest,
    verify_source_integrity,
)


# ---------------------------------------------------------------------------
# Source integrity
# ---------------------------------------------------------------------------
class TestSourceIntegrity:
    def test_digest_is_sha256_hex(self):
        d = genome_integrity_digest()
        assert len(d) == 64 and all(c in "0123456789abcdef" for c in d)

    def test_pinned_hash_matches_live_genome(self):
        if GENOME_INTEGRITY_HASH == "PIN_AT_BUILD_TIME":
            pytest.skip("integrity hash not pinned yet")
        assert verify_source_integrity() is True

    def test_digest_is_deterministic(self):
        assert genome_integrity_digest() == genome_integrity_digest()


# ---------------------------------------------------------------------------
# Module 1: mesh extrusion
# ---------------------------------------------------------------------------
class TestVolumetricMesh:
    def test_square_extrusion_topology(self):
        mesh = VolumetricMeshExporter(z_depth=10.0)
        obj = mesh.extrude_polygon_path([(0, 0), (10, 0), (10, 10), (0, 10)])
        verts = [l for l in obj.splitlines() if l.startswith("v ")]
        faces = [l for l in obj.splitlines() if l.startswith("f ")]
        assert len(verts) == 8  # 4 front + 4 back
        # 2 triangles per cap * 2 caps + 4 side quads = 8 faces
        assert len(faces) == 8

    def test_concave_polygon_triangulated(self):
        mesh = VolumetricMeshExporter()
        concave = [(0, 0), (10, 0), (10, 10), (5, 5), (0, 10)]
        tris = mesh.triangulate(concave)
        # Area of triangles must equal the polygon's area (shoelace).
        area = sum(
            abs(
                (concave[a][0] * (concave[b][1] - concave[c][1])
                 + concave[b][0] * (concave[c][1] - concave[a][1])
                 + concave[c][0] * (concave[a][1] - concave[b][1]))
            ) / 2.0
            for a, b, c in tris
        )
        assert math.isclose(area, abs(mesh._signed_area(concave)), rel_tol=1e-9)

    def test_degenerate_input_rejected(self):
        with pytest.raises(ValueError):
            VolumetricMeshExporter().extrude_polygon_path([(0, 0), (1, 1)])


# ---------------------------------------------------------------------------
# Module 2: watermarking
# ---------------------------------------------------------------------------
class TestVectorWatermark:
    def test_round_trip_exact(self):
        stego = ZKVectorSteganographer(tolerance=0.02)
        contour = [(float(i), float(i % 7)) for i in range(80)]
        marked = stego.embed_bitstream(contour, "ARI_KEY")
        assert stego.extract_bitstream(contour, marked, 7) == "ARI_KEY"

    def test_oversized_payload_raises(self):
        stego = ZKVectorSteganographer()
        with pytest.raises(CapacityError):
            stego.embed_bitstream([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], "TOO_LONG")

    def test_perturbation_within_tolerance(self):
        stego = ZKVectorSteganographer(tolerance=0.01)
        contour = [(float(i), 0.0) for i in range(40)]
        marked = stego.embed_bitstream(contour, "AB")
        assert all(
            abs(a[0] - b[0]) <= 0.01 + 1e-9 for a, b in zip(contour, marked)
        )

    def test_unicode_payload_round_trips(self):
        stego = ZKVectorSteganographer()
        contour = [(float(i), 0.0) for i in range(64)]
        payload = "λ⟁"
        marked = stego.embed_bitstream(contour, payload)
        assert stego.extract_bitstream(contour, marked, len(payload.encode())) == payload


# ---------------------------------------------------------------------------
# Module 3: latent space over real glyph geometry
# ---------------------------------------------------------------------------
class TestLatentSpace:
    def test_uses_real_genome_52_glyphs(self):
        aligner = LatentSpaceTensorAligner()
        assert aligner.feature_matrix.shape == (52, 10)
        assert aligner.feature_matrix.dtype == np.float64

    def test_matrices_are_consistent(self):
        aligner = LatentSpaceTensorAligner()
        m = aligner.compute_pairwise_tensor_matrix()
        assert m["euclidean_distance"].shape == (52, 52)
        assert m["cosine_similarity"].shape == (52, 52)
        # cosine similarity of a vector with itself is 1
        assert np.allclose(np.diag(m["cosine_similarity"]), 1.0, atol=1e-9)
        # euclidean distance to itself is 0
        assert np.allclose(np.diag(m["euclidean_distance"]), 0.0, atol=1e-12)

    def test_family_report_is_structured(self):
        report = LatentSpaceTensorAligner().family_similarity_report()
        assert {"within_family_cosine", "across_family_cosine"} <= report.keys()

    def test_matrix_is_the_real_genome_not_random(self):
        from rytt.advanced_suite import _load_genome
        genome, _ = _load_genome()
        a1 = LatentSpaceTensorAligner()
        a2 = LatentSpaceTensorAligner()
        # Deterministic across instances...
        assert np.array_equal(a1.feature_matrix, a2.feature_matrix)
        # ...and every row equals the live genome vector for its glyph.
        for key, row in zip(a1.glyph_keys, a1.feature_matrix):
            assert np.allclose(row, genome[key]["vectors"])


# ---------------------------------------------------------------------------
# Module 4: DNA encoding
# ---------------------------------------------------------------------------
class TestDNAEncoding:
    def test_ascii_round_trip(self):
        d = DNADataSynthesizer()
        p = {"type": "ARI_STREAM", "symbol": "TH"}
        assert d.dna_to_ari(d.ari_to_dna(p)) == p

    def test_non_ascii_round_trip(self):
        d = DNADataSynthesizer()
        for p in [
            {"symbol": "λ"},
            {"glyph": "⟁⟆⟇"},
            {"text": "échelle naïve — test"},
        ]:
            assert d.dna_to_ari(d.ari_to_dna(p)) == p

    def test_only_valid_bases(self):
        d = DNADataSynthesizer()
        seq = d.ari_to_dna({"x": 1})
        assert set(seq) <= {"A", "C", "G", "T"}

    def test_analyze_reports_real_constraints(self):
        d = DNADataSynthesizer()
        stats = d.analyze(d.ari_to_dna({"symbol": "TH"}))
        assert 0.0 <= stats["gc_content"] <= 1.0
        assert stats["longest_homopolymer_run"] >= 1
        assert stats["bases"] % 4 == 0

    def test_malformed_length_rejected(self):
        with pytest.raises(ValueError):
            DNADataSynthesizer().dna_to_ari("ACG")  # not a multiple of 4 bases


# ---------------------------------------------------------------------------
# Module 5: Burau braid representation
# ---------------------------------------------------------------------------
class TestBurauBraid:
    def test_braid_relations_hold(self):
        for n in (3, 4, 5):
            for t in (0.2, 0.5, 0.8):
                assert BurauBraidCompiler(num_strands=n).verify_braid_relations(t=t)

    def test_adjacent_generators_do_not_commute(self):
        qc = BurauBraidCompiler(num_strands=4)
        u12 = qc.burau_matrix([("sigma", 1), ("sigma", 2)])
        u21 = qc.burau_matrix([("sigma", 2), ("sigma", 1)])
        assert not np.allclose(u12, u21)

    def test_distant_generators_commute(self):
        qc = BurauBraidCompiler(num_strands=4)
        u13 = qc.burau_matrix([("sigma", 1), ("sigma", 3)])
        u31 = qc.burau_matrix([("sigma", 3), ("sigma", 1)])
        assert np.allclose(u13, u31)

    def test_yang_baxter_word_equality(self):
        qc = BurauBraidCompiler(num_strands=4)
        w1 = [("sigma", 1), ("sigma", 2), ("sigma", 1)]
        w2 = [("sigma", 2), ("sigma", 1), ("sigma", 2)]
        assert np.allclose(qc.burau_matrix(w1), qc.burau_matrix(w2))

    def test_inverse_generators_annihilate(self):
        qc = BurauBraidCompiler(num_strands=4)
        m = qc.burau_matrix([("sigma", 2), ("sigma_inv", 2)])
        assert np.allclose(m, np.eye(4), atol=1e-9)

    def test_phrase_map_is_deterministic_and_alpha_only(self):
        qc = BurauBraidCompiler(num_strands=4)
        assert qc.phrase_to_braid_generators("MAN DALA!") == qc.phrase_to_braid_generators("MAN DALA!")
        assert all(1 <= s <= 3 for _, s in qc.phrase_to_braid_generators("ZYXW"))

    def test_invalid_generator_rejected(self):
        qc = BurauBraidCompiler(num_strands=4)
        with pytest.raises(ValueError):
            qc.burau_generator(4)


class TestEntrypointsActuallyRun:
    """Scripts must survive being RUN, not merely imported.

    The suite imports functions and asserts on their return values, which never
    executes the `main()` bodies. That gap let a real defect ship: a leftover
    `_work_dir` reference in embedding_init.main() -- a name bound in no scope --
    so `python3 src/rytt/embedding_init.py` raised NameError before writing a
    single artifact, while every test stayed green.

    These tests execute the entrypoints in a subprocess, which is the only way
    to catch a NameError that lives on a path imports never take.
    """

    def _run(self, rel, tmp_path):
        import subprocess, sys, os, shutil
        repo = Path(__file__).resolve().parent.parent
        env = dict(os.environ, PYTHONPATH=str(repo / "src"))
        return subprocess.run([sys.executable, str(repo / rel)],
                              capture_output=True, text=True, timeout=600,
                              cwd=str(repo), env=env)

    def test_embedding_init_main_runs(self, tmp_path):
        r = self._run("src/rytt/embedding_init.py", tmp_path)
        assert r.returncode == 0, f"entrypoint failed:\n{r.stderr[-1500:]}"
        assert "NameError" not in r.stderr

    def test_embedding_init_writes_artifacts(self, tmp_path):
        import json
        repo = Path(__file__).resolve().parent.parent
        self._run("src/rytt/embedding_init.py", tmp_path)
        report = repo / "artifacts" / "embedding_init_report.json"
        assert report.is_file(), "main() must write its report artifact"
        d = json.loads(report.read_text())["geometric_matrix"]
        # The headline claim: family structure is real, not noise.
        assert d["family_diff"] > 0.15, f"family separation collapsed: {d['family_diff']}"
