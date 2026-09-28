"""RYTT Hugging Face tokenizer adapter.

Wraps the RYTT engine in a PreTrainedTokenizerFast-compatible interface
so downstream models (PyTorch, vLLM) can consume dual-plane token streams
directly. Separates token IDs into base identifiers and plane indicators,
enabling neural networks to project Ground Plane (z=0) and Elevated Plane
(z=25) tokens into distinct positional embeddings.

Usage:
    from rytt.tokenizer import RyttTokenizer
    tok = RyttTokenizer()
    result = tok.encode_dual_plane("RYTT transforms language")
    # result = {"input_ids": [...], "plane_ids": [...], "attention_mask": [...]}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_TOKENIZER_PATH = Path(__file__).parent / "data" / "tokenizer.json"


class RyttTokenizer:
    """Hugging Face-compatible tokenizer wrapping the RYTT dual-plane engine.

    Falls back to the pure-Python reference compiler when the Rust-backed
    `rytt._rytt` extension is not installed.
    """

    def __init__(self, tokenizer_file: Optional[str] = None, **kwargs: Any) -> None:
        self._tokenizer_path = Path(tokenizer_file) if tokenizer_file else _TOKENIZER_PATH
        self._config = json.loads(self._tokenizer_path.read_text())

        # Special tokens
        self.bos_token = "<|rytt_bos|>"
        self.eos_token = "<|rytt_eos|>"
        self.unk_token = "<|rytt_unk|>"
        self.pad_token = "<|rytt_pad|>"

        # Try to load the Rust-backed fast tokenizer
        self._fast_backend = None
        try:
            from rytt._rytt import encode as _rust_encode, decode as _rust_decode
            self._fast_backend = (_rust_encode, _rust_decode)
        except ImportError:
            pass

        # Fall back to pure-Python compiler
        if self._fast_backend is None:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
            from rytt.compiler import RyttCompiler
            self._compiler = RyttCompiler()

    @property
    def vocab_size(self) -> int:
        """Total vocabulary size including special tokens and PUA code points."""
        return 4 + 0xF8FF - 0xE000 + 1  # 4 specials + BMP PUA range

    def _encode_text(self, text: str) -> List[int]:
        """Encode text to a list of PUA token code points."""
        if self._fast_backend:
            encode_fn, _ = self._fast_backend
            envelope_json = encode_fn(text)
            envelope = json.loads(envelope_json)
            return [t["token"] for t in envelope["token_trace"]]
        else:
            result = self._compiler.compile(text)
            return [ord(c) if len(c) == 1 else 0 for c in result.encoded_pua]

    def encode_dual_plane(self, text: str) -> Dict[str, List[int]]:
        """Encode text into dual-plane token streams.

        Returns a dict with:
            input_ids: base token IDs (code point & 0x7FFF)
            plane_ids: plane indicator (1 for Elevated z=25, 0 for Ground z=0)
            attention_mask: all ones
        """
        token_cps = self._encode_text(text)

        # Separate base IDs and plane indicators
        # Elevated plane tokens (U+E800+) have bit 0x800 set
        input_ids = [(cp & 0x7FFF) for cp in token_cps]
        plane_ids = [1 if (cp & 0x8000) else 0 for cp in token_cps]

        # Add BOS/EOS special tokens
        input_ids = [1] + input_ids + [2]  # BOS + tokens + EOS
        plane_ids = [-1] + plane_ids + [-1]  # specials have no plane
        attention_mask = [1] * len(input_ids)

        return {
            "input_ids": input_ids,
            "plane_ids": plane_ids,
            "attention_mask": attention_mask,
        }

    def __call__(self, text: str, **kwargs: Any) -> Dict[str, List[int]]:
        """Standard tokenizer call interface."""
        return self.encode_dual_plane(text)
