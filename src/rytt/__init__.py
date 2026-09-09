"""RYTT Sovereign Semiotics — public API."""
from .compiler import (
    RyttCompiler,
    RyttCompilationResult,
    RyttToken,
    RYTT_GENOME,
    RYTT_LIGATURES,
    PUA_TO_PLAIN,
)
try:
    from .tokenizer import RyttNativeTokenizer  # optional module
except ImportError:
    class RyttNativeTokenizer:  # type: ignore
        """Stub — install rytt[tokenizer] for the full tokenizer."""
        def __init__(self, *a, **kw): raise NotImplementedError("rytt[tokenizer] not installed")

try:
    from .benchmark import RyttBenchmarkEngine  # optional module
except ImportError:
    class RyttBenchmarkEngine:  # type: ignore
        """Stub — install rytt[dev] for the benchmark engine."""
        def __init__(self, *a, **kw): raise NotImplementedError("rytt[dev] not installed")

__version__ = "0.1.0"
__all__ = [
    "RyttCompiler", "RyttCompilationResult", "RyttToken",
    "RYTT_GENOME", "RYTT_LIGATURES", "PUA_TO_PLAIN",
    "RyttNativeTokenizer", "RyttBenchmarkEngine",
    "__version__",
]
