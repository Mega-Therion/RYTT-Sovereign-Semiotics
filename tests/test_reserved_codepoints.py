"""The display serialization reserves two character classes (spec/vocabulary.json, display_serialization):
U+00B7 is the literal-space marker, and the allocated RYTT PUA codepoints carry the genome and chords. The spec
defines no escape for either, so source text containing them does not round-trip. These tests pin that domain:
everything outside it must round-trip, and the reserved cases are strict xfails, so adding an escape rule turns
them into failures that force this file and the spec to be updated together."""
import pytest

from rytt.compiler import PUA_TO_PLAIN, RyttCompiler

ROUND_TRIP = ["", " ", "hello world", "Hello, World!  ", "café 😀", "Tab\there", "line\nbreak",
              "\ue7ff", "\uf8ff", "Ωμέγα ∑ ∫", "mixed CASE 123 #@!"]
RESERVED = ["·", "a·b", next(iter(PUA_TO_PLAIN))]


@pytest.mark.parametrize("text", ROUND_TRIP)
def test_round_trip_outside_reserved_classes(text):
    c = RyttCompiler()
    assert c.decompile(c.compile(text).encoded_pua) == text


@pytest.mark.xfail(strict=True, reason="spec defines no escape for U+00B7 or allocated RYTT PUA codepoints")
@pytest.mark.parametrize("text", RESERVED)
def test_reserved_classes_do_not_round_trip(text):
    c = RyttCompiler()
    assert c.decompile(c.compile(text).encoded_pua) == text
