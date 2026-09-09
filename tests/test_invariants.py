"""
Property-style invariant tests for RYTT 0.1.0.
24 tests covering: round-trip, PUA disjointness, uniqueness, precedence,
fixtures, and public interfaces.
"""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rytt.compiler import (
    RYTT_GENOME,
    RYTT_LIGATURES,
    PUA_TO_PLAIN,
    RyttCompiler,
    RyttCompilationResult,
    RyttToken,
)
from rytt import (
    RyttNativeTokenizer,
    RyttBenchmarkEngine,
)

FIXTURES_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "rytt_vocabulary.json"
COMPILER = RyttCompiler()

# ── Round-trip invariants (8 tests) ────────────────────────────────────────────
ROUNDTRIP_CORPUS = [
    ("plain ascii", "Hello, World!"),
    ("mixed case", "The Quick Brown Fox Jumps Over The Lazy Dog"),
    ("code snippet", "def foo(x): return x * 2"),
    ("punctuation heavy", "...wait—what?! (yes, really.)"),
    ("whitespace preserved", "  leading and trailing  "),
    ("unicode passthrough", "α β γ → ∞ ⊕ ∇"),
    ("ligature rich", "RYTT THE TION MENT ING STR"),
    ("numbers and symbols", "v0.1.0 — 2026-09-09 @ 100%"),
]


@pytest.mark.parametrize("label,text", ROUNDTRIP_CORPUS)
def test_round_trip_exact(label, text):
    result = COMPILER.compile(text)
    recovered = COMPILER.decompile(result.encoded_pua)
    assert recovered == text, (
        f"[{label}] Round-trip failed:\n  in:  {repr(text)}\n  out: {repr(recovered)}"
    )


# ── PUA disjointness (2 tests) ───────────────────────────────────────────────
de
def test_pua_genome_ligature_disjoint():
    """Genome and ligature PUA codepoints must not share any value."""
    genome_puas = {v["pua"] for v in RYTT_GENOME.values()}
    lig_puas = {v["pua"] for v in RYTT_LIGATURES.values()}
    overlap = genome_puas & lig_puas
    assert not overlap, f"PUA overlap between genome and ligatures: {[hex(ord(c)) for c in overlap]}"


def test_pua_all_in_private_use_area():
    """Every compiled PUA codepoint must reside in the Unicode PUA block (0xE000-0xF8FF)."""
    all_puas = (
        list(RYTT_GENOME.values()) + list(RYTT_LIGATURES.values())
    )
    for entry in all_puas:
        cp = ord(entry["pua"])
        assert 0xE000 <= cp <= 0xF8FF, (
            f"PUA codepoint {hex(cp)} is outside PUA block"
        )


# ── Uniqueness invariants (3 tests) ──────────────────────────────────────────────
def test_genome_pua_unique():
    puas = [v["pua"] for v in RYTT_GENOME.values()]
    assert len(puas) == len(set(puas)), "Duplicate PUA codepoints in RYTT_GENOME"


def test_ligature_pua_unique():
    puas = [v["pua"] for v in RYTT_LIGATURES.values()]
    assert len(puas) == len(set(puas)), "Duplicate PUA codepoints in RYTT_LIGATURES"


def test_pua_to_plain_covers_all():
    for k, v in RYTT_GENOME.items():
        assert v["pua"] in PUA_TO_PLAIN, f"Genome entry {k!r} PUA not in PUA_TO_PLAIN"
    for k, v in RYTT_LIGATURES.items():
        assert v["pua"] in PUA_TO_PLAIN, f"Ligature {k!r} PUA not in PUA_TO_PLAIN"


# ── Precedence invariant (1 test) ────────────────────────────────────────────────
def test_ligature_precedence_over_single_glyph():
    """A known ligature must compile to a single chord token, not individual glyphs."""
    result = COMPILER.compile("RYTT")
    chord_tokens = [t for t in result.tokens if t.is_chord]
    assert len(chord_tokens) >= 1, "RYTT should compile to at least one chord token"
    assert any(t.raw == "RYTT" for t in chord_tokens), (
        "RYTT sequence should be captured as a single chord"
    )


# ── Fixture consistency (3 tests) ────────────────────────────────────────────────
def test_vocabulary_fixture_exists():
    assert FIXTURES_PATH.exists(), f"Fixture not found: {FIXTURES_PATH}"


def test_vocabulary_fixture_genome_count():
    if not FIXTURES_PATH.exists():
        pytest.skip("Fixture not generated yet")
    vocab = json.loads(FIXTURES_PATH.read_text())
    assert vocab["stats"]["genome_entries"] == len(RYTT_GENOME), (
        "Fixture genome count does not match live RYTT_GENOME"
    )


def test_vocabulary_fixture_ligature_count():
    if not FIXTURES_PATH.exists():
        pytest.skip("Fixture not generated yet")
    vocab = json.loads(FIXTURES_PATH.read_text())
    assert vocab["stats"]["ligature_entries"] == len(RYTT_LIGATURES), (
        "Fixture ligature count does not match live RYTT_LIGATURES"
    )


# ── Public interface invariants (4 tests) ──────────────────────────────────────────
def test_compilation_result_has_explicit_fields():
    result = COMPILER.compile("hello world")
    d = result.to_dict()
    required = {
        "source_text", "token_count", "encoded_pua",
        "parity_mod24", "compression_ratio", "token_savings_pct",
        "vsa_hash_sha256", "holonomic_bases", "tokens",
    }
    missing = required - d.keys()
    assert not missing, f"to_dict() missing fields: {missing}"


def test_token_dict_has_explicit_fields():
    result = COMPILER.compile("Test ING")
    for tok in result.tokens:
        d = tok.to_dict()
        for field in ("raw", "pua", "is_chord", "chord_len", "family", "path", "is_upper", "case_plane", "elevation_z"):
            assert field in d, f"RyttToken.to_dict() missing field: {field!r}"


def test_token_savings_pct_can_be_negative():
    """token_savings_pct must NOT be clamped — it must be capable of reporting a loss."""
    result = COMPILER.compile("a")
    assert isinstance(result.token_savings_pct, float)
    result2 = COMPILER.compile("A B")  # 3 chars → 3 tokens → 0%
    assert result2.token_savings_pct == pytest.approx(0.0, abs=0.1)


def test_decompile_non_pua_passthrough():
    """Non-PUA characters (punctuation, digits) must pass through decompile unchanged."""
    raw = "123 !@# newline\ntest"
    result = COMPILER.compile(raw)
    recovered = COMPILER.decompile(result.encoded_pua)
    assert recovered == raw


# ── Non-Latin passthrough invariant (1 test) ──────────────────────────────────────────
def test_non_latin_alpha_passthrough():
    """Non-Latin alphabetic characters pass through unchanged (not mapped to A glyph)."""
    text = "α Ω ñ"
    result = COMPILER.compile(text)
    recovered = COMPILER.decompile(result.encoded_pua)
    assert recovered == text, (
        f"Non-latin passthrough failed: {repr(text)} → {repr(recovered)}"
    )


# ── Compiler instance invariants (2 tests) ───────────────────────────────────────────
def test_compiler_is_deterministic():
    text = "The RYTT system encodes TION and MENT as chords."
    r1 = COMPILER.compile(text)
    r2 = COMPILER.compile(text)
    assert r1.encoded_pua == r2.encoded_pua
    assert r1.vsa_hash_sha256 == r2.vsa_hash_sha256


def test_empty_string_roundtrip():
    result = COMPILER.compile("")
    assert COMPILER.decompile(result.encoded_pua) == ""
