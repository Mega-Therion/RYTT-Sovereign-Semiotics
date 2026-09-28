"""Hypothesis property-based fuzzing for the RYTT Python runtime.

Generates high-entropy Unicode text across edge-case categories and
asserts the round-trip invariant decode(encode(s)) == s for every input.

Run with: pytest tests/test_fuzz_hypothesis.py -v
"""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st, HealthCheck

import sys
sys.path.insert(0, "src")
from rytt.compiler import RyttCompiler

compiler = RyttCompiler()

# Strategy: broad Unicode text with no category blacklist (includes Cs, Mn, Mc, Me, Cf)
unicode_broad = st.text(
    alphabet=st.characters(blacklist_categories=()),
    min_size=0,
    max_size=500,
)

# Strategy: surrogate code points specifically (Cs category)
unicode_surrogates = st.text(
    alphabet=st.characters(whitelist_categories=("Cs",)),
    min_size=1,
    max_size=50,
)

# Strategy: combining marks (Mn, Mc, Me)
unicode_combining = st.text(
    alphabet=st.characters(whitelist_categories=("Mn", "Mc", "Me")),
    min_size=1,
    max_size=50,
)

# Strategy: format characters (Cf) — bidi controls, ZWJ, etc.
unicode_format = st.text(
    alphabet=st.characters(whitelist_categories=("Cf",)),
    min_size=1,
    max_size=50,
)

# Strategy: mixed ASCII genome + Unicode edge cases
unicode_mixed = st.text(
    alphabet=st.sampled_from([
        'a', 'b', 'c', 'z', 'A', 'Z', 'R', 'Y', 'T',
        ' ', '\n', '\t', '!', '.', ',', '0', '9',
        '\u00e9', '\u0301', '\u0300', '\u0302', '\u0303',
        '\u2066', '\u2067', '\u2068', '\u2069',
        '\u202a', '\u202e', '\u202c',
        '\u200d', '\ufe0f', '\ufe0e',
        '\u0623', '\u05e9', '\u4eac', '\U0001f525',
    ]),
    min_size=0,
    max_size=200,
)


@settings(max_examples=2000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=unicode_broad)
def test_hypothesis_roundtrip_broad(text):
    """Round-trip must hold for arbitrary Unicode text."""
    result = compiler.compile(text)
    decoded = compiler.decompile(result.encoded_pua)
    assert text == decoded, f"Round-trip failed: {text!r} != {decoded!r}"


@settings(max_examples=500, deadline=None)
@given(text=unicode_combining)
def test_hypothesis_roundtrip_combining_marks(text):
    """Round-trip must hold for strings of combining marks (Mn, Mc, Me)."""
    result = compiler.compile(text)
    decoded = compiler.decompile(result.encoded_pua)
    assert text == decoded, f"Combining marks round-trip failed: {text!r} != {decoded!r}"


@settings(max_examples=500, deadline=None)
@given(text=unicode_format)
def test_hypothesis_roundtrip_format_chars(text):
    """Round-trip must hold for format characters (Cf: bidi, ZWJ, etc.)."""
    result = compiler.compile(text)
    decoded = compiler.decompile(result.encoded_pua)
    assert text == decoded, f"Format chars round-trip failed: {text!r} != {decoded!r}"


@settings(max_examples=500, deadline=None)
@given(text=unicode_mixed)
def test_hypothesis_roundtrip_mixed(text):
    """Round-trip must hold for mixed ASCII genome + Unicode edge cases."""
    result = compiler.compile(text)
    decoded = compiler.decompile(result.encoded_pua)
    assert text == decoded, f"Mixed round-trip failed: {text!r} != {decoded!r}"


@settings(max_examples=200, deadline=None)
@given(text=unicode_surrogates)
def test_hypothesis_roundtrip_surrogates(text):
    """Round-trip for surrogate code points.

    The Python runtime uses surrogatepass semantics — unpaired surrogates
    pass through unchanged. The VSA hash step may fail on surrogates since
    they cannot be UTF-8 encoded; this test verifies the tokenization and
    decompile path is lossless even when the VSA step is bypassed.
    """
    # Surrogates crash the VSA hash; test the token/decompile path directly
    # by monkey-patching the VSA method to use surrogatepass encoding.
    import hashlib
    _orig = compiler._generate_10240_vsa_hypervector
    def _safe_vsa(pua_stream, parity):
        try:
            return _orig(pua_stream, parity)
        except UnicodeEncodeError:
            seed = f"{compiler.author_seal}:{parity}".encode('utf-8')
            h = hashlib.sha256(seed + pua_stream.encode('utf-8', 'surrogatepass')).digest()
            return [0] * 1280, h.hex()
    compiler._generate_10240_vsa_hypervector = _safe_vsa
    try:
        result = compiler.compile(text)
        decoded = compiler.decompile(result.encoded_pua)
        assert text == decoded, f"Surrogate round-trip failed: {text!r} != {decoded!r}"
    finally:
        compiler._generate_10240_vsa_hypervector = _orig
