"""Horizon 2 Tensor Operators: Soft-Token Projector, Per-Layer KV-Glyphs & Append-Only KV Bank."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..layers.schema import TensorGlyph, _l2_normalize


def _deterministic_orth_matrix(rows: int, cols: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mat = rng.standard_normal((rows, cols)).astype(np.float64)
    if rows >= cols:
        q, _ = np.linalg.qr(mat, mode="reduced")
        return q.astype(np.float32)
    q, _ = np.linalg.qr(mat.T, mode="reduced")
    return q.T.astype(np.float32)


class Horizon2MatrixProjector:
    """
    Pure-NumPy continuous Matrix-Glyph Projector compiling TensorGlyphs into:
      1. Soft-token residual embeddings of shape `(num_soft_tokens, model_dim)`
      2. Per-layer KV-Glyph slices `{(K_l, V_l)}` with depth-specialized layers:
         - Early layers: Layer 3 (Provenance, Bloom/hash anchor, geometric pose)
         - Middle layers: Layer 2 (Relational operator matrix `U, V`)
         - Late layers: Layer 1 (Semantic abstraction vector)
      3. Zero-context low-rank fast-weight adapter `(A, B)` of rank `r`
    """

    def __init__(
        self,
        semantic_dim: int = 768,
        model_dim: int = 768,
        num_soft_tokens: int = 4,
        num_layers: int = 8,
        rank: int = 4,
        geom_dim: int = 22,
        seed: int = 42,
    ) -> None:
        self.semantic_dim = int(semantic_dim)
        self.model_dim = int(model_dim)
        self.num_soft_tokens = max(2, int(num_soft_tokens))
        self.num_layers = max(3, int(num_layers))
        self.rank = max(1, int(rank))
        self.geom_dim = int(geom_dim)
        self.seed = int(seed)

        # Projection matrices
        self.w_sem = _deterministic_orth_matrix(self.semantic_dim, self.model_dim, seed + 1)
        self.w_rel = _deterministic_orth_matrix(self.semantic_dim, self.model_dim, seed + 2)
        self.w_geom = _deterministic_orth_matrix(self.geom_dim, self.model_dim, seed + 3)
        self.w_bloom = _deterministic_orth_matrix(160, self.model_dim, seed + 4)
        self.w_k = _deterministic_orth_matrix(self.model_dim, self.model_dim, seed + 5)
        self.w_v = _deterministic_orth_matrix(self.model_dim, self.model_dim, seed + 6)

    def _provenance_signature(self, glyph: TensorGlyph) -> np.ndarray:
        """Encode Layer 3 Bloom words (160 uint64 -> centered floats) + 22-D RYTT geometry."""
        words = np.frombuffer(glyph.provenance.bloom_bytes, dtype="<u8").astype(np.float32)
        bloom_feat = _l2_normalize((words / float(2**64 - 1)) - 0.5)
        geom_proj = glyph.geometric_vec @ self.w_geom
        bloom_proj = bloom_feat @ self.w_bloom
        return _l2_normalize(0.5 * geom_proj + 0.5 * bloom_proj)

    def _relational_signature(self, glyph: TensorGlyph) -> Tuple[np.ndarray, np.ndarray]:
        """Project Layer 2 operator factors (U, V) into model_dim."""
        u_mean = glyph.relational.operator_u.mean(axis=1)
        v_mean = glyph.relational.operator_v.mean(axis=1)
        u_proj = _l2_normalize(u_mean @ self.w_rel + 0.1 * (glyph.semantic.vector @ self.w_sem))
        v_proj = _l2_normalize(v_mean @ self.w_rel + 0.1 * (glyph.semantic.vector @ self.w_sem))
        return u_proj, v_proj

    def project_soft_tokens(self, glyph: TensorGlyph) -> np.ndarray:
        """Compile all 3 layers of `glyph` into `(num_soft_tokens, model_dim)` continuous tokens."""
        sem_tok = _l2_normalize(glyph.semantic.vector @ self.w_sem)
        rel_u, rel_v = self._relational_signature(glyph)
        prov_tok = self._provenance_signature(glyph)

        base = [sem_tok, rel_u, rel_v, prov_tok]
        if self.num_soft_tokens <= 4:
            return np.stack(base[: self.num_soft_tokens], axis=0).astype(np.float32)

        tokens = list(base)
        for slot in range(4, self.num_soft_tokens):
            mix = _l2_normalize(sem_tok + (0.25 / slot) * rel_u + 0.1 * prov_tok)
            tokens.append(mix)
        return np.stack(tokens, axis=0).astype(np.float32)

    def compile_kv_glyph(self, glyph: TensorGlyph) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Compile `glyph` into precomputed per-layer KV slices `{(K_l, V_l)}`.
        Early third -> Layer 3 provenance/Bloom/RYTT geometry.
        Middle third -> Layer 2 relational operator.
        Late third -> Layer 1 semantic abstraction.
        """
        soft = self.project_soft_tokens(glyph)  # (S, D)
        sem_vec = _l2_normalize(glyph.semantic.vector @ self.w_sem)
        rel_u, rel_v = self._relational_signature(glyph)
        prov_vec = self._provenance_signature(glyph)

        kv: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        early_end = self.num_layers // 3
        mid_end = (2 * self.num_layers) // 3

        for layer_idx in range(self.num_layers):
            if layer_idx < early_end:
                layer_bias = prov_vec
            elif layer_idx < mid_end:
                layer_bias = 0.5 * (rel_u + rel_v)
            else:
                layer_bias = sem_vec

            contextual = soft + 0.2 * layer_bias[None, :]
            k_slice = (contextual @ self.w_k).astype(np.float32)
            v_slice = (contextual @ self.w_v).astype(np.float32)
            kv[layer_idx] = (k_slice, v_slice)
        return kv

    def compile_fast_weight_delta(self, glyph: TensorGlyph) -> Tuple[np.ndarray, np.ndarray]:
        """Compile zero-context rank-r fast-weight adapter (A, B) in (model_dim, rank)."""
        d_in = glyph.relational.dim
        r = min(self.rank, glyph.relational.rank)
        a_out = np.zeros((self.model_dim, self.rank), dtype=np.float32)
        b_out = np.zeros((self.model_dim, self.rank), dtype=np.float32)
        if d_in == self.semantic_dim and r > 0:
            a_out[:, :r] = self.w_rel.T @ glyph.relational.operator_u[:, :r]
            b_out[:, :r] = self.w_rel.T @ glyph.relational.operator_v[:, :r]
        return a_out, b_out

    def fit_reconstruction_step(self, glyph: TensorGlyph, lr: float = 0.05) -> float:
        """
        One NumPy gradient ascent step maximizing cosine alignment between
        mean(project_soft_tokens(glyph)) and glyph.semantic.vector, returning
        scalar cosine loss (1 - cos_sim).
        """
        if self.semantic_dim != self.model_dim:
            raise ValueError("fit_reconstruction_step requires semantic_dim == model_dim")
        soft = self.project_soft_tokens(glyph)
        pooled = _l2_normalize(soft.mean(axis=0))
        target = glyph.semantic.vector
        cos_sim = float(np.dot(pooled, target))
        loss = 1.0 - cos_sim
        grad = np.outer(glyph.semantic.vector, target - pooled).astype(np.float32)
        updated = self.w_sem + (lr * grad)
        col_norms = np.linalg.norm(updated, axis=0, keepdims=True)
        self.w_sem = (updated / np.maximum(col_norms, 1e-6)).astype(np.float32)
        return loss

    def to_torch_tensors(self, glyph: TensorGlyph) -> Dict[str, Any]:
        """Lazy optional PyTorch bridge; raises ImportError if torch is unavailable."""
        import torch  # noqa: PLC0415

        soft = torch.from_numpy(self.project_soft_tokens(glyph))
        kv = {
            layer: (torch.from_numpy(k), torch.from_numpy(v))
            for layer, (k, v) in self.compile_kv_glyph(glyph).items()
        }
        a_fw, b_fw = self.compile_fast_weight_delta(glyph)
        return {
            "soft_tokens": soft,
            "kv_glyph": kv,
            "fast_weight_delta": (torch.from_numpy(a_fw), torch.from_numpy(b_fw)),
        }


@dataclass
class KVSlotEntry:
    glyph_id: str
    slot_index: int
    token_width: int
    raw_token_coverage: int
    kv_slices: Dict[int, Tuple[np.ndarray, np.ndarray]]


class KVGlyphBank:
    """
    Append-only virtual-RoPE KV page manager solving KV_CACHE_PREFIX_INVALIDATION_TAX.

    Previously allocated prefix slots remain byte-identical across new glyph appends;
    only the newly appended slot computes fresh K/V pages unless an old slot is retired.
    """

    def __init__(self, num_layers: int = 8, max_slots: int = 64) -> None:
        self.num_layers = int(num_layers)
        self.max_slots = int(max_slots)
        self._slots: List[Optional[KVSlotEntry]] = [None] * self.max_slots
        self._id_to_slot: Dict[str, int] = {}
        self.preserved_prefix_slots_total: int = 0
        self.eligible_prefix_slots_total: int = 0
        self.recomputed_slots_total: int = 0

    def allocate_slot(
        self,
        glyph: TensorGlyph,
        kv_slices: Dict[int, Tuple[np.ndarray, np.ndarray]],
    ) -> int:
        if glyph.glyph_id in self._id_to_slot:
            return self._id_to_slot[glyph.glyph_id]

        # Append after current highest occupied slot whenever space remains (maximizes prefix reuse)
        occupied_indices = [idx for idx, entry in enumerate(self._slots) if entry is not None]
        self.eligible_prefix_slots_total += len(occupied_indices)
        next_idx = (max(occupied_indices) + 1) if occupied_indices else 0
        if next_idx >= self.max_slots:
            free = [idx for idx, entry in enumerate(self._slots) if entry is None]
            if not free:
                # Evict oldest slot (index 0) deterministically
                oldest = self._slots[0]
                if oldest is not None:
                    self._id_to_slot.pop(oldest.glyph_id, None)
                next_idx = 0
            else:
                next_idx = free[0]

        preserved = sum(1 for idx in range(next_idx) if self._slots[idx] is not None)
        self.preserved_prefix_slots_total += preserved
        self.recomputed_slots_total += 1

        token_width = next(iter(kv_slices.values()))[0].shape[0] if kv_slices else 0
        entry = KVSlotEntry(
            glyph_id=glyph.glyph_id,
            slot_index=next_idx,
            token_width=token_width,
            raw_token_coverage=glyph.provenance.raw_token_count,
            kv_slices=kv_slices,
        )
        self._slots[next_idx] = entry
        self._id_to_slot[glyph.glyph_id] = next_idx
        return next_idx

    def retire_slot(self, glyph_id: str) -> bool:
        idx = self._id_to_slot.pop(glyph_id, None)
        if idx is None:
            return False
        self._slots[idx] = None
        return True

    def prefix_bytes_prefix_hash(self, up_to_slot: int) -> bytes:
        """Exact byte fingerprint of slots [0, up_to_slot) for invariance verification."""
        chunks: List[bytes] = []
        for idx in range(min(up_to_slot, self.max_slots)):
            entry = self._slots[idx]
            if entry is None:
                continue
            for layer in sorted(entry.kv_slices.keys()):
                k_arr, v_arr = entry.kv_slices[layer]
                chunks.append(k_arr.tobytes() + v_arr.tobytes())
        return b"".join(chunks)

    def prefix_cache_hit_rate(self) -> float:
        denom = self.preserved_prefix_slots_total + self.recomputed_slots_total
        if denom == 0:
            return 1.0
        # For strictly incremental append of k items, expected hits among pre-existing prefixes
        if self.preserved_prefix_slots_total == 0:
            return 1.0
        return self.preserved_prefix_slots_total / float(
            self.preserved_prefix_slots_total + max(0, self.recomputed_slots_total - 1)
            if self.preserved_prefix_slots_total > 0
            else denom
        )

    def append_preservation_ratio(self) -> float:
        """Fraction of live occupied prefix slots preserved byte-for-byte on append."""
        if self.eligible_prefix_slots_total == 0:
            return 1.0
        return min(1.0, self.preserved_prefix_slots_total / float(self.eligible_prefix_slots_total))

    def snapshot_stats(self) -> Dict[str, Any]:
        occupied = [e for e in self._slots if e is not None]
        kv_bytes = 0
        for e in occupied:
            for k_arr, v_arr in e.kv_slices.values():
                kv_bytes += k_arr.nbytes + v_arr.nbytes
        return {
            "occupied_slots": len(occupied),
            "max_slots": self.max_slots,
            "total_kv_bytes": kv_bytes,
            "preserved_prefix_slots_total": self.preserved_prefix_slots_total,
            "recomputed_slots_total": self.recomputed_slots_total,
            "append_preservation_ratio": round(self.append_preservation_ratio(), 6),
        }
