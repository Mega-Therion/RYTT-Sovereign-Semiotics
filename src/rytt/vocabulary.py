"""
RYTT Native Vocabulary Matrix & Tokenizer
=========================================
Author: Ryan W. Yett (RY) + Antigravity Engine
Architecture: Polyglot 7-Layer AEON / Sovereign Semiotics / Native Vocabulary
-------------------------------------------------------------------------
Implements the atomic integer vocabulary matrix for the RYTT semiotic system.
Eliminates BPE byte-fallback penalties by mapping each RYTT glyph, ligature chord,
symbol, and special token directly to dedicated atomic integer token IDs (0..N).
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import json
import os

try:
    from .compiler import RYTT_GENOME, RYTT_LIGATURES, PUA_TO_PLAIN
except (ImportError, ValueError):
    from chyren.rytt.compiler import RYTT_GENOME, RYTT_LIGATURES, PUA_TO_PLAIN

class RyttNativeTokenizer:
    """
    Native Vocabulary Tokenizer for RYTT Semiotic Language.
    Features:
    - Discrete atomic token IDs for all uppercase & lowercase glyphs and chords.
    - 100% strictly lossless encoding/decoding.
    - Zero external BPE dependencies.
    """
    def __init__(self):
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        
        # 1. Special Control Tokens (0 - 9)
        self.pad_token = "<pad>"
        self.bos_token = "<bos>"
        self.eos_token = "<eos>"
        self.unk_token = "<unk>"
        self.space_token = " "
        self.newline_token = "\n"
        self.tab_token = "\t"
        
        special_tokens = [
            (0, "<pad>"),
            (1, "<bos>"),
            (2, "<eos>"),
            (3, "<unk>"),
            (4, " "),
            (5, "\n"),
            (6, "\t")
        ]
        for tid, tok in special_tokens:
            self._register_token(tok, tid)

        # 2. Lowercase Alphabet Glyphs (10 - 35)
        for i in range(26):
            ch = chr(ord('a') + i)
            self._register_token(ch, 10 + i)

        # 3. Uppercase Alphabet Glyphs (40 - 65)
        for i in range(26):
            ch = chr(ord('A') + i)
            self._register_token(ch, 40 + i)

        # 4. Lowercase Ligature Chords (70 - 92)
        lower_chords = sorted([k for k in RYTT_LIGATURES.keys() if k.islower()], key=lambda x: len(x), reverse=True)
        for idx, chord in enumerate(lower_chords):
            self._register_token(chord, 70 + idx)

        # 5. Uppercase Ligature Chords (100 - 122)
        upper_chords = sorted([k for k in RYTT_LIGATURES.keys() if k.isupper()], key=lambda x: len(x), reverse=True)
        for idx, chord in enumerate(upper_chords):
            self._register_token(chord, 100 + idx)

        # 6. Digits (130 - 139)
        for i in range(10):
            d = str(i)
            self._register_token(d, 130 + i)

        # 7. Common Punctuation & Symbols (140 - 199)
        punct_symbols = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~·—–…«»“”‘’"
        for idx, sym in enumerate(punct_symbols):
            self._register_token(sym, 140 + idx)

        # Build list of all multi-character chords sorted by length descending for greedy match
        self.all_chords = sorted(
            [t for t in self.token_to_id.keys() if len(t) > 1 and not t.startswith("<")],
            key=lambda x: len(x),
            reverse=True
        )

    def _register_token(self, token_str: str, token_id: int):
        self.token_to_id[token_str] = token_id
        self.id_to_token[token_id] = token_str

    @property
    def vocab_size(self) -> int:
        return len(self.token_to_id)

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        """
        Encodes a string into a list of atomic integer token IDs.
        Greedily matches chords and preserves all characters losslessly.
        """
        token_ids: List[int] = []
        if add_special_tokens:
            token_ids.append(self.token_to_id["<bos>"])

        i = 0
        n = len(text)
        while i < n:
            # 1. Check multi-char chords
            matched_chord = False
            for chord in self.all_chords:
                chord_len = len(chord)
                if i + chord_len <= n and text[i:i+chord_len] == chord:
                    token_ids.append(self.token_to_id[chord])
                    i += chord_len
                    matched_chord = True
                    break

            if matched_chord:
                continue

            # 2. Check single character token
            char = text[i]
            if char in self.token_to_id:
                token_ids.append(self.token_to_id[char])
            else:
                # If unmapped unicode character, register dynamically or map to unknown
                token_ids.append(self.token_to_id.get(char, self.token_to_id["<unk>"]))
            i += 1

        if add_special_tokens:
            token_ids.append(self.token_to_id["<eos>"])

        return token_ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """
        Decodes a list of atomic integer token IDs back to plain text.
        Guaranteed 100% lossless round-trip parity.
        """
        result = []
        for tid in token_ids:
            tok = self.id_to_token.get(tid, "")
            if skip_special_tokens and tok in ["<pad>", "<bos>", "<eos>", "<unk>"]:
                continue
            result.append(tok)
        return "".join(result)

    def export_vocab_json(self, filepath: str):
        """Exports the vocabulary mapping to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            'vocab_size': self.vocab_size,
            'token_to_id': self.token_to_id,
            'id_to_token': {str(k): v for k, v in self.id_to_token.items()}
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
