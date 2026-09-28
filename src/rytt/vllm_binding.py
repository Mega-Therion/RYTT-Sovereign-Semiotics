"""vLLM custom dispatch binding for RYTT token streams.

Provides a C++ dispatch interface that routes RYTT dual-plane token streams
directly to GPU memory via PagedAttention, avoiding the Python GIL.

This is a stub that defines the interface contract. The actual C++
implementation would be compiled as a vLLM plugin and registered via
the vLLM custom tokenizer API.

Interface:
    class RyttVLLMDispatch:
        def encode(self, text: str) -> RyttTokenBatch
        def decode(self, token_ids: List[int], plane_ids: List[int]) -> str
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional


class RyttTokenBatch:
    """A batch of RYTT tokens ready for GPU dispatch."""

    def __init__(self, input_ids: List[int], plane_ids: List[int],
                 attention_mask: List[int], seq_lens: List[int]):
        self.input_ids = input_ids
        self.plane_ids = plane_ids
        self.attention_mask = attention_mask
        self.seq_lens = seq_lens

    def to_gpu_tensors(self) -> Dict[str, Any]:
        """Convert to GPU tensor descriptors (stub — real impl uses PyTorch CUDA)."""
        return {
            "input_ids": self.input_ids,
            "plane_ids": self.plane_ids,
            "attention_mask": self.attention_mask,
            "seq_lens": self.seq_lens,
            "device": "cuda",
        }


class RyttVLLMDispatch:
    """Custom vLLM dispatch for RYTT dual-plane token streams.

    Routes token streams directly to GPU memory via PagedAttention,
    separating Ground Plane (z=0) and Elevated Plane (z=25) tokens into
    distinct positional embedding projections.
    """

    def __init__(self, tokenizer_path: Optional[str] = None):
        from rytt.tokenizer import RyttTokenizer
        self.tokenizer = RyttTokenizer(tokenizer_path)

    def encode(self, text: str) -> RyttTokenBatch:
        """Encode text into a GPU-ready token batch."""
        result = self.tokenizer.encode_dual_plane(text)
        return RyttTokenBatch(
            input_ids=result["input_ids"],
            plane_ids=result["plane_ids"],
            attention_mask=result["attention_mask"],
            seq_lens=[len(result["input_ids"])],
        )

    def encode_batch(self, texts: List[str]) -> RyttTokenBatch:
        """Encode a batch of texts into a single GPU-ready batch."""
        all_input_ids = []
        all_plane_ids = []
        all_attention = []
        seq_lens = []

        for text in texts:
            result = self.tokenizer.encode_dual_plane(text)
            all_input_ids.extend(result["input_ids"])
            all_plane_ids.extend(result["plane_ids"])
            all_attention.extend(result["attention_mask"])
            seq_lens.append(len(result["input_ids"]))

        return RyttTokenBatch(all_input_ids, all_plane_ids, all_attention, seq_lens)

    def decode(self, token_ids: List[int], plane_ids: Optional[List[int]] = None) -> str:
        """Decode token IDs back to text (stub — requires inverse PUA mapping)."""
        # Reconstruct PUA code points from base IDs and plane indicators
        if plane_ids:
            cps = [
                tid | (0x8000 if pid == 1 else 0)
                for tid, pid in zip(token_ids, plane_ids)
                if pid >= 0  # skip special tokens
            ]
        else:
            cps = token_ids

        # Convert code points back to characters
        chars = []
        for cp in cps:
            if 0xE000 <= cp <= 0xF8FF:
                # PUA token — needs inverse genome/ligature mapping
                # This is a stub; the real implementation would use the
                # inverse mapping from the canonical spec
                chars.append(chr(cp))
            elif cp <= 4:
                # Special token — skip
                continue
            else:
                chars.append(chr(cp))
        return "".join(chars)
