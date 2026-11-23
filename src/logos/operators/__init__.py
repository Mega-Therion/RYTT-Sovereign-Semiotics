"""O — Dual-Horizon Injection Operators (Text & Continuous Tensor/KV)."""
from .horizon1_text import Horizon1TextOperator
from .horizon2_tensor import Horizon2MatrixProjector, KVGlyphBank, KVSlotEntry
from .torch_projector import (
    HAS_TORCH,
    GlyphConditionedAttentionLM,
    NumpyMatrixGlyphTrainer,
    ProjectedGlyphBundle,
    TorchMatrixGlyphProjector,
    extract_glyph_feature_bundle,
    train_projector_on_glyphs,
)

__all__ = [
    "GlyphConditionedAttentionLM",
    "HAS_TORCH",
    "Horizon1TextOperator",
    "Horizon2MatrixProjector",
    "KVGlyphBank",
    "KVSlotEntry",
    "NumpyMatrixGlyphTrainer",
    "ProjectedGlyphBundle",
    "TorchMatrixGlyphProjector",
    "extract_glyph_feature_bundle",
    "train_projector_on_glyphs",
]
