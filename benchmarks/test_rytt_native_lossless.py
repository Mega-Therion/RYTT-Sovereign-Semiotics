"""
Tests for Native RYTT Dual-Plane Lossless Semiotic Architecture & Native Tokenizer
===================================================================================
Author: Ryan W. Yett (RY) + Antigravity Engine
"""

import pytest
import sys
import os

# Ensure package is on sys.path
sys.path.insert(0, "/home/mega/Chyren/Codebase/l5_meaning/python")

from chyren.rytt.compiler import RyttCompiler, RYTT_GENOME, RYTT_LIGATURES, PUA_TO_PLAIN
from chyren.rytt.vocabulary import RyttNativeTokenizer


class TestRyttDualPlaneLossless:
    """Test suite for dual-plane case preserving RYTT compiler."""

    def setup_method(self):
        self.compiler = RyttCompiler()

    def test_single_word_mixed_case(self):
        words = ["Tyger", "ChatGPT", "DNA", "Chyren", "SovereignOS", "Python3", "OpenAI"]
        for word in words:
            compiled = self.compiler.compile(word)
            decompiled = self.compiler.decompile(compiled.compiled_text)
            assert decompiled == word, f"Mismatch for '{word}': got '{decompiled}'"

    def test_classic_poem_lossless(self):
        text = "Tyger Tyger, burning bright,\nIn the forests of the night;"
        compiled = self.compiler.compile(text)
        decompiled = self.compiler.decompile(compiled.compiled_text)
        assert decompiled == text

    def test_all_uppercase_vs_all_lowercase(self):
        lower = "the quick brown fox jumps over the lazy dog"
        upper = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
        
        c_lower = self.compiler.compile(lower)
        c_upper = self.compiler.compile(upper)
        
        assert self.compiler.decompile(c_lower.compiled_text) == lower
        assert self.compiler.decompile(c_upper.compiled_text) == upper
        
        # Verify that lower and upper produce distinct PUA code points
        assert c_lower.compiled_text != c_upper.compiled_text
        
        # Verify elevation coordinates
        for tok in c_lower.tokens:
            if tok.raw.isalpha():
                assert tok.case_plane == 0
                assert tok.elevation_z == 0.0
                assert not tok.is_upper
                
        for tok in c_upper.tokens:
            if tok.raw.isalpha():
                assert tok.case_plane == 1
                assert tok.elevation_z == 25.0
                assert tok.is_upper

    def test_chords_dual_plane(self):
        # Test lowercase chord vs uppercase chord
        c_tion = self.compiler.compile("tion")
        c_TION = self.compiler.compile("TION")
        
        assert self.compiler.decompile(c_tion.compiled_text) == "tion"
        assert self.compiler.decompile(c_TION.compiled_text) == "TION"
        assert c_tion.compiled_text != c_TION.compiled_text


class TestRyttNativeTokenizer:
    """Test suite for atomic integer native vocabulary tokenizer."""

    def setup_method(self):
        self.tokenizer = RyttNativeTokenizer()

    def test_vocab_registration(self):
        assert len(self.tokenizer.token_to_id) >= 100
        assert "<bos>" in self.tokenizer.token_to_id
        assert "<eos>" in self.tokenizer.token_to_id
        assert "a" in self.tokenizer.token_to_id
        assert "A" in self.tokenizer.token_to_id
        assert "tion" in self.tokenizer.token_to_id
        assert "TION" in self.tokenizer.token_to_id

    def test_encode_decode_round_trip(self):
        texts = [
            "Hello World!",
            "Tyger Tyger burning bright",
            "Sovereignty 2026",
            "Chyren 7-layer polyglot architecture."
        ]
        for t in texts:
            encoded = self.tokenizer.encode(t, add_special_tokens=False)
            assert isinstance(encoded, list)
            assert all(isinstance(x, int) for x in encoded)
            
            decoded = self.tokenizer.decode(encoded, skip_special_tokens=True)
            assert decoded == t, f"Decoded mismatch for '{t}': got '{decoded}'"

    def test_token_reduction_vs_raw_chars(self):
        text = "information and intentional distribution of traditional generation"
        # Chords like tion, and, al, in should compress
        encoded = self.tokenizer.encode(text, add_special_tokens=False)
        assert len(encoded) < len(text)
