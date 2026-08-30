"""
Test: Glyph Atlas Data Consistency
==================================
Verifies that the glyph and chord data embedded in the renderers
matches the canonical source in src/rytt/compiler.py.

Run: python3 -m pytest benchmarks/test_glyph_atlas_data.py -v
"""

import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from rytt.compiler import RYTT_GENOME, RYTT_LIGATURES


class TestGlyphAtlasDataConsistency:
    """Verify renderer embedded data matches compiler.py source."""

    def test_primitive_count(self):
        upper_primitives = [k for k in RYTT_GENOME if len(k) == 1 and k.isupper()]
        assert len(upper_primitives) == 26, f"Expected 26 primitives, got {len(upper_primitives)}"

    def test_chord_count(self):
        upper_chords = [k for k in RYTT_LIGATURES if k.isupper()]
        assert len(upper_chords) == 23, f"Expected 23 chords, got {len(upper_chords)}"

    def test_all_primitives_have_paths(self):
        for char, spec in RYTT_GENOME.items():
            if char.isupper():
                assert spec.get('path'), f"Glyph {char} missing SVG path"
                assert spec.get('family'), f"Glyph {char} missing family"

    def test_all_chords_have_paths_and_meanings(self):
        for chord, spec in RYTT_LIGATURES.items():
            if chord.isupper():
                assert spec.get('path'), f"Chord {chord} missing SVG path"
                assert spec.get('meaning'), f"Chord {chord} missing meaning"

    def test_chord_lengths(self):
        for chord in RYTT_LIGATURES:
            if chord.isupper():
                assert 2 <= len(chord) <= 4, f"Chord {chord} has unexpected length {len(chord)}"

    def test_dual_plane_coverage(self):
        """Every primitive and chord should have both ground and elevated forms."""
        for char in [k for k in RYTT_GENOME if k.isupper()]:
            assert char.lower() in RYTT_GENOME, f"Missing lowercase form for {char}"
            assert RYTT_GENOME[char]['case_plane'] == 1
            assert RYTT_GENOME[char.lower()]['case_plane'] == 0

        for chord in [k for k in RYTT_LIGATURES if k.isupper()]:
            assert chord.lower() in RYTT_LIGATURES, f"Missing lowercase form for {chord}"

    def test_atlas_html_contains_all_glyphs(self):
        """Check that glyph_atlas.html embeds all 26 primitive paths."""
        atlas_path = os.path.join(os.path.dirname(__file__), '..', 'renderers', 'glyph_atlas.html')
        if not os.path.exists(atlas_path):
            return  # Skip if file doesn't exist (e.g. running outside repo)

        with open(atlas_path) as f:
            content = f.read()

        for char in [k for k in RYTT_GENOME if k.isupper()]:
            path = RYTT_GENOME[char]['path']
            # Check that the path data appears in the atlas HTML
            assert path in content, f"Atlas HTML missing SVG path for glyph {char}"

    def test_atlas_html_contains_all_chords(self):
        """Check that glyph_atlas.html embeds all 23 chord paths."""
        atlas_path = os.path.join(os.path.dirname(__file__), '..', 'renderers', 'glyph_atlas.html')
        if not os.path.exists(atlas_path):
            return

        with open(atlas_path) as f:
            content = f.read()

        for chord in [k for k in RYTT_LIGATURES if k.isupper()]:
            path = RYTT_LIGATURES[chord]['path']
            assert path in content, f"Atlas HTML missing SVG path for chord {chord}"
