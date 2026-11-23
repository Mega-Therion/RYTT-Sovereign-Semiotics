"""Layer 1 Semantic Embedders (Deterministic Spectral + Optional Live Ollama)."""
from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np

from .schema import _l2_normalize

_WORD_RE = re.compile(r"[A-Za-z0-9_./:-]{2,}")


class Embedder(Protocol):
    dim: int
    backend_name: str

    def embed(self, text: str) -> Tuple[np.ndarray, str]:
        ...


class DeterministicSpectralEmbedder:
    """
    Zero-dependency NumPy signed random projection embedder.

    Combines word unigrams, bigrams, and character 3-grams via BLAKE2b signed
    hashing into a fixed D-dimensional L2-normalized float32 vector.
    """

    def __init__(self, dim: int = 768) -> None:
        if dim < 16:
            raise ValueError(f"Embedding dim must be >= 16, got {dim}")
        self.dim = int(dim)
        self.backend_name = "deterministic-spectral"

    def _feature_counts(self, text: str) -> Dict[str, float]:
        counts: Dict[str, float] = {}
        words = [w.lower() for w in _WORD_RE.findall(text)]
        for idx, word in enumerate(words):
            key = f"w:{word}"
            counts[key] = counts.get(key, 0.0) + 2.0
            if idx + 1 < len(words):
                bi = f"b:{word}_{words[idx + 1]}"
                counts[bi] = counts.get(bi, 0.0) + 1.5
            padded = f"^{word}$"
            if len(padded) >= 3:
                for pos in range(len(padded) - 2):
                    tri = f"c:{padded[pos : pos + 3]}"
                    counts[tri] = counts.get(tri, 0.0) + 0.6
        return counts

    def embed(self, text: str) -> Tuple[np.ndarray, str]:
        vec = np.zeros(self.dim, dtype=np.float32)
        features = self._feature_counts(text)
        if not features:
            vec[0] = 1.0
            return vec, self.backend_name

        for feat, raw_weight in features.items():
            weight = 1.0 + math.log1p(raw_weight)
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=16).digest()
            for probe in range(4):
                off = probe * 4
                idx = int.from_bytes(digest[off : off + 3], "big") % self.dim
                sign = 1.0 if (digest[off + 3] & 1) == 0 else -1.0
                vec[idx] += np.float32(sign * weight)

        return _l2_normalize(vec), self.backend_name

    def embed_batch(self, texts: List[str]) -> List[Tuple[np.ndarray, str]]:
        return [self.embed(t) for t in texts]


class OllamaEmbedder:
    """
    Live Ollama embeddings client (`nomic-embed-text:latest` default) with
    automatic cached lookup and fail-safe fallback to DeterministicSpectralEmbedder.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text:latest",
        base_url: str = "http://127.0.0.1:11434",
        dim: int = 768,
        timeout: float = 5.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dim = int(dim)
        self.timeout = float(timeout)
        self.backend_name = f"ollama:{model}"
        self.fallback = DeterministicSpectralEmbedder(dim=self.dim)
        self.last_fallback: bool = False
        self._cache: Dict[str, Tuple[np.ndarray, str]] = {}

    def _fit_dim(self, arr: np.ndarray) -> np.ndarray:
        if arr.shape[0] == self.dim:
            return _l2_normalize(arr)
        if arr.shape[0] > self.dim:
            return _l2_normalize(arr[: self.dim])
        out = np.zeros(self.dim, dtype=np.float32)
        out[: arr.shape[0]] = arr
        return _l2_normalize(out)

    def embed(self, text: str) -> Tuple[np.ndarray, str]:
        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{self.base_url}/api/embeddings"
        payload = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            emb = body.get("embedding")
            if not isinstance(emb, list) or not emb:
                raise ValueError("Missing 'embedding' array from Ollama response")
            arr = self._fit_dim(np.asarray(emb, dtype=np.float32))
            self.last_fallback = False
            result = (arr, self.backend_name)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
            self.last_fallback = True
            result = self.fallback.embed(text)

        self._cache[cache_key] = result
        return result


def build_embedder(
    use_ollama: bool = False,
    model: str = "nomic-embed-text:latest",
    base_url: str = "http://127.0.0.1:11434",
    dim: int = 768,
) -> DeterministicSpectralEmbedder | OllamaEmbedder:
    """Factory selecting deterministic or Ollama embeddings cleanly."""
    if use_ollama:
        return OllamaEmbedder(model=model, base_url=base_url, dim=dim)
    return DeterministicSpectralEmbedder(dim=dim)
