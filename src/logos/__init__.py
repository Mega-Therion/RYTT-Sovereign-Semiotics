"""
L.O.G.O.S. — Layered Operator-Glyph Orchestration System.

Five-part holographic virtual-memory architecture built over RYTT Sovereign Semiotics:
  L (layers)       : 3-Layer Tensor-Glyph Compiler + 10,240-bit Bloom MMU
  O (operators)    : Horizon 1 Text Operator + Horizon 2 Soft-Token / KV-Glyph Projector
  G (glyphs)       : Dual-Plane RYTT Geometry & Logarithmic Rollup Merkle-VSA Tree
  O (orchestrator) : Semantic Episode Splitter + Dynamic LOD Viewport Camera
  S (substrate)    : Immutable SQLite WAL Store, `.logos` Cartridges & Empirical Benchmark
"""
from .glyphs import DualPlaneGlyphTree
from .layers import (
    BLOOM_BITS,
    BLOOM_BYTES,
    BloomFilter10240,
    BloomHit,
    BloomMMU,
    DeltaExtractionResult,
    DeterministicSpectralEmbedder,
    EpistemicTier,
    LogosLayerCompiler,
    NaturalLanguageDeltaExtractor,
    OllamaEmbedder,
    OllamaStateDeltaExtractor,
    ProvenanceLayer,
    RelationalLayer,
    RelationEdge,
    RelationType,
    SemanticLayer,
    TensorGlyph,
    build_embedder,
    extract_entities,
    normalize_slot_key,
)
from .operators import (
    GlyphConditionedAttentionLM,
    Horizon1TextOperator,
    Horizon2MatrixProjector,
    KVGlyphBank,
    NumpyMatrixGlyphTrainer,
    ProjectedGlyphBundle,
    TorchMatrixGlyphProjector,
    train_projector_on_glyphs,
)
from .orchestrator import HydratedSlice, LogosOrchestrator, SemanticEpisodeSplitter, TurnRecord, ViewportFrame
from .session import LogosSession
from .substrate import (
    LogosSubstrate,
    build_unstructured_long_horizon_workload,
    export_cartridge,
    load_cartridge,
    merge_cartridges,
    run_logos_benchmark,
    run_long_horizon_eval,
    verify_cartridge,
)

__version__ = "0.4.0"

__all__ = [
    "BLOOM_BITS",
    "BLOOM_BYTES",
    "BloomFilter10240",
    "BloomHit",
    "BloomMMU",
    "DeltaExtractionResult",
    "DeterministicSpectralEmbedder",
    "DualPlaneGlyphTree",
    "EpistemicTier",
    "GlyphConditionedAttentionLM",
    "Horizon1TextOperator",
    "Horizon2MatrixProjector",
    "HydratedSlice",
    "KVGlyphBank",
    "LogosLayerCompiler",
    "LogosOrchestrator",
    "LogosSession",
    "LogosSubstrate",
    "NaturalLanguageDeltaExtractor",
    "NumpyMatrixGlyphTrainer",
    "OllamaEmbedder",
    "OllamaStateDeltaExtractor",
    "ProjectedGlyphBundle",
    "ProvenanceLayer",
    "RelationEdge",
    "RelationType",
    "RelationalLayer",
    "SemanticEpisodeSplitter",
    "SemanticLayer",
    "TensorGlyph",
    "TorchMatrixGlyphProjector",
    "TurnRecord",
    "ViewportFrame",
    "__version__",
    "build_embedder",
    "build_unstructured_long_horizon_workload",
    "export_cartridge",
    "extract_entities",
    "load_cartridge",
    "merge_cartridges",
    "normalize_slot_key",
    "run_logos_benchmark",
    "run_long_horizon_eval",
    "train_projector_on_glyphs",
    "verify_cartridge",
]
