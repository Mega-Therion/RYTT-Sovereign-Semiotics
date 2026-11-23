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
    DeterministicSpectralEmbedder,
    EpistemicTier,
    LogosLayerCompiler,
    OllamaEmbedder,
    ProvenanceLayer,
    RelationalLayer,
    RelationEdge,
    RelationType,
    SemanticLayer,
    TensorGlyph,
    build_embedder,
    extract_entities,
)
from .operators import Horizon1TextOperator, Horizon2MatrixProjector, KVGlyphBank
from .orchestrator import HydratedSlice, LogosOrchestrator, SemanticEpisodeSplitter, TurnRecord, ViewportFrame
from .session import LogosSession
from .substrate import LogosSubstrate, export_cartridge, load_cartridge, run_logos_benchmark, verify_cartridge

__version__ = "0.1.0"

__all__ = [
    "BLOOM_BITS",
    "BLOOM_BYTES",
    "BloomFilter10240",
    "BloomHit",
    "BloomMMU",
    "DeterministicSpectralEmbedder",
    "DualPlaneGlyphTree",
    "EpistemicTier",
    "Horizon1TextOperator",
    "Horizon2MatrixProjector",
    "HydratedSlice",
    "KVGlyphBank",
    "LogosLayerCompiler",
    "LogosOrchestrator",
    "LogosSession",
    "LogosSubstrate",
    "OllamaEmbedder",
    "ProvenanceLayer",
    "RelationEdge",
    "RelationType",
    "RelationalLayer",
    "SemanticEpisodeSplitter",
    "SemanticLayer",
    "TensorGlyph",
    "TurnRecord",
    "ViewportFrame",
    "__version__",
    "build_embedder",
    "export_cartridge",
    "extract_entities",
    "load_cartridge",
    "run_logos_benchmark",
    "verify_cartridge",
]
