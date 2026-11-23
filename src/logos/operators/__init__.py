"""O — Dual-Horizon Injection Operators (Text & Continuous Tensor/KV)."""
from .horizon1_text import Horizon1TextOperator
from .horizon2_tensor import Horizon2MatrixProjector, KVGlyphBank, KVSlotEntry

__all__ = [
    "Horizon1TextOperator",
    "Horizon2MatrixProjector",
    "KVGlyphBank",
    "KVSlotEntry",
]
