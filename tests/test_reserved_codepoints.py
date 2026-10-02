"""The display stream reserves U+00B7 (the literal-space marker) and the RYTT PUA range U+E000..U+F8FF (spec
encoding.pua). Source characters in either class are written behind the display escape, U+0020, which no encoder
otherwise emits. These tests pin four things: every text round-trips, reserved characters take exactly the escaped
form, the escape is a pure extension (streams without U+0020 decode as they did before it existed), and a stream
that ends in a bare escape is rejected."""

import random

import pytest

from rytt.compiler import (
    DISPLAY_ESCAPE,
    PUA_TO_PLAIN,
    RyttCompiler,
    is_reserved_display_char,
)
from rytt.interchange import build_envelope, verify_envelope

ROUND_TRIP = [
    "",
    " ",
    "hello world",
    "Hello, World!  ",
    "café 😀",
    "Tab\there",
    "line\nbreak",
    "",
    "",
    "Ωμέγα ∑ ∫",
    "mixed CASE 123 #@!",
]
RESERVED = [
    "·",
    "a·b",
    "··",
    " · ",
    next(iter(PUA_TO_PLAIN)),
    "",
    "",
    "",
    "",
    "",
    "TIONtion",
    "a",
]


def _decode_before_escape(stream):
    """The decoder as it was before the escape existed."""
    return "".join(" " if ch == "·" else PUA_TO_PLAIN.get(ch, ch) for ch in stream)


@pytest.mark.parametrize("text", ROUND_TRIP + RESERVED)
def test_round_trip(text):
    c = RyttCompiler()
    assert c.decompile(c.compile(text).encoded_pua) == text


def test_reserved_characters_take_the_escaped_form():
    c = RyttCompiler()
    assert c.compile("·").encoded_pua == " ·"
    assert c.compile("a·b").encoded_pua == " ·"
    assert c.compile("").encoded_pua == "  "
    token = c.compile("·").tokens[0]
    assert (token.raw, token.pua, token.family, token.case_plane) == (
        "·",
        " ·",
        "ESCAPE",
        -1,
    )


def test_reserved_set_is_the_space_marker_and_the_whole_pua_range():
    assert is_reserved_display_char("·")
    assert is_reserved_display_char("") and is_reserved_display_char("")
    assert not is_reserved_display_char("\udfff") and not is_reserved_display_char("豈")
    assert not is_reserved_display_char(
        "\U000f0000"
    )  # supplementary PUA is outside the declared range
    assert not is_reserved_display_char(" ") and not is_reserved_display_char("a")


def test_display_never_carries_a_reserved_source_character_unescaped():
    c = RyttCompiler()
    rng = random.Random(7)
    alphabet = list("aeiotrnzAEIOTRYZ \n\t!?%—éα東😀·") + ["", "", "", "", ""]
    for _ in range(500):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 40)))
        stream = c.compile(text).encoded_pua
        assert c.decompile(stream) == text
        i = 0
        while i < len(stream):
            if stream[i] == DISPLAY_ESCAPE:
                assert is_reserved_display_char(stream[i + 1])
                i += 2
                continue
            # An unescaped PUA codepoint is always an allocated glyph or chord.
            assert not (0xE000 <= ord(stream[i]) <= 0xF8FF) or stream[i] in PUA_TO_PLAIN
            i += 1


def test_streams_without_the_escape_decode_as_before():
    c = RyttCompiler()
    rng = random.Random(11)
    alphabet = list("·\n\t!?%—éα東😀") + list(PUA_TO_PLAIN)[:20] + ["", ""]
    for _ in range(500):
        stream = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 40)))
        assert DISPLAY_ESCAPE not in stream
        assert c.decompile(stream) == _decode_before_escape(stream)


def test_sources_without_reserved_characters_encode_as_before():
    # The escape adds no token and changes no codepoint unless the source holds a reserved character.
    c = RyttCompiler()
    for text in ROUND_TRIP:
        if any(is_reserved_display_char(ch) for ch in text):
            continue
        stream = c.compile(text).encoded_pua
        assert DISPLAY_ESCAPE not in stream
        assert _decode_before_escape(stream) == text


def test_dangling_escape_is_rejected():
    c = RyttCompiler()
    with pytest.raises(ValueError, match="dangling escape"):
        c.decompile(" ")
    envelope = build_envelope("·")
    envelope["encoded_display"] = " "
    result = verify_envelope(envelope)
    assert not result["valid"]
    assert any("dangling escape" in error for error in result["errors"])
