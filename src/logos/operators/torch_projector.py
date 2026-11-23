"""Horizon 2 Completion: Trainable Multi-Layer Tensor-Glyph Projector & Direct Soft-Token / KV Attention LM."""
from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..layers.schema import TensorGlyph, _l2_normalize
from .horizon2_tensor import KVGlyphBank, _deterministic_orth_matrix

HAS_TORCH: bool = importlib.util.find_spec("torch") is not None


def extract_glyph_feature_bundle(
    glyph: TensorGlyph,
    semantic_dim: int = 768,
    rank: int = 4,
    geom_dim: int = 22,
) -> Dict[str, np.ndarray]:
    """
    Extract normalized numeric feature tensors from a 3-layer TensorGlyph:
      - Layer 1 `semantic_vec`: (semantic_dim,)
      - Layer 2 `rel_u`, `rel_v`: (semantic_dim, rank) + pooled vectors
      - RYTT Geometry `geom_vec`: (geom_dim,)
      - Layer 3 `bloom_vec`: (160,) exact per-uint64-word bit density in [-0.5, 0.5]
    """
    sem = np.zeros(semantic_dim, dtype=np.float32)
    src_sem = glyph.semantic.vector.reshape(-1)
    k_sem = min(semantic_dim, src_sem.shape[0])
    sem[:k_sem] = src_sem[:k_sem]
    sem = _l2_normalize(sem)

    rel_u = np.zeros((semantic_dim, rank), dtype=np.float32)
    rel_v = np.zeros((semantic_dim, rank), dtype=np.float32)
    u_src = glyph.relational.operator_u
    v_src = glyph.relational.operator_v
    d_rel = min(semantic_dim, u_src.shape[0])
    r_rel = min(rank, u_src.shape[1])
    rel_u[:d_rel, :r_rel] = u_src[:d_rel, :r_rel]
    rel_v[:d_rel, :r_rel] = v_src[:d_rel, :r_rel]

    u_pool = _l2_normalize(rel_u.mean(axis=1) + 0.15 * sem)
    v_pool = _l2_normalize(rel_v.mean(axis=1) + 0.15 * sem)

    geom = np.zeros(geom_dim, dtype=np.float32)
    g_src = glyph.geometric_vec.reshape(-1)
    k_g = min(geom_dim, g_src.shape[0])
    geom[:k_g] = g_src[:k_g]
    geom = _l2_normalize(geom)

    # Exact bit density per 64-bit word across all 160 words (10,240 bits)
    bits = np.unpackbits(np.frombuffer(glyph.provenance.bloom_bytes, dtype=np.uint8))
    word_density = bits.reshape(160, 64).mean(axis=1).astype(np.float32) - 0.5
    bloom_vec = _l2_normalize(word_density)

    return {
        "semantic_vec": sem,
        "rel_u": rel_u,
        "rel_v": rel_v,
        "rel_u_pool": u_pool,
        "rel_v_pool": v_pool,
        "geom_vec": geom,
        "bloom_vec": bloom_vec,
    }


@dataclass
class ProjectedGlyphBundle:
    """Continuous neural representation of an archived TensorGlyph (0 text tokens)."""

    glyph_id: str
    inputs_embeds: np.ndarray  # (batch, k, hidden_dim)
    past_key_values: Dict[int, Tuple[np.ndarray, np.ndarray]]  # layer -> (K, V) of shape (batch, heads, k, head_dim)
    kv_bank_slices: Dict[int, Tuple[np.ndarray, np.ndarray]]  # layer -> (K_2d, V_2d) of shape (k, hidden_dim)
    fast_weight_a: np.ndarray  # (batch, hidden_dim, rank)
    fast_weight_b: np.ndarray  # (batch, hidden_dim, rank)
    reconstructed_semantic: np.ndarray  # (batch, semantic_dim)
    reconstructed_relational: np.ndarray  # (batch, semantic_dim)


class NumpyMatrixGlyphTrainer:
    """
    Pure-NumPy analytical forward + backward engine for `TorchMatrixGlyphProjector`.

    Provides identical tensor shapes and trainable parameters so CI environments
    without PyTorch can train, evaluate, and verify Horizon 2 end-to-end.
    """

    def __init__(
        self,
        semantic_dim: int = 128,
        hidden_dim: int = 128,
        num_soft_tokens: int = 4,
        num_layers: int = 6,
        num_heads: int = 4,
        rank: int = 4,
        geom_dim: int = 22,
        seed: int = 42,
    ) -> None:
        if hidden_dim % num_heads != 0:
            raise ValueError(f"hidden_dim ({hidden_dim}) must be divisible by num_heads ({num_heads})")
        self.semantic_dim = int(semantic_dim)
        self.hidden_dim = int(hidden_dim)
        self.num_soft_tokens = max(2, int(num_soft_tokens))
        self.num_layers = max(3, int(num_layers))
        self.num_heads = max(1, int(num_heads))
        self.head_dim = self.hidden_dim // self.num_heads
        self.rank = max(1, int(rank))
        self.geom_dim = int(geom_dim)
        self.seed = int(seed)

        # Learnable projection weights (initialized with small non-aligned random weights so training converges visibly)
        rng = np.random.default_rng(seed)
        scale = 1.0 / math.sqrt(self.semantic_dim)
        self.w_sem = (rng.standard_normal((self.semantic_dim, self.hidden_dim)) * scale).astype(np.float32)
        self.w_rel_u = (rng.standard_normal((self.semantic_dim, self.hidden_dim)) * scale).astype(np.float32)
        self.w_rel_v = (rng.standard_normal((self.semantic_dim, self.hidden_dim)) * scale).astype(np.float32)
        self.w_geom = _deterministic_orth_matrix(self.geom_dim, self.hidden_dim, seed + 10) * 0.5
        self.w_bloom = _deterministic_orth_matrix(160, self.hidden_dim, seed + 11) * 0.5
        self.slot_bias = (rng.standard_normal((self.num_soft_tokens, self.hidden_dim)) * 0.05).astype(np.float32)

        # Depth-specialized KV projections (Early=L3 Provenance, Mid=L2 Relational, Late=L1 Semantic)
        self.w_k_layers = [
            _deterministic_orth_matrix(self.hidden_dim, self.hidden_dim, seed + 20 + l)
            for l in range(self.num_layers)
        ]
        self.w_v_layers = [
            _deterministic_orth_matrix(self.hidden_dim, self.hidden_dim, seed + 50 + l)
            for l in range(self.num_layers)
        ]

        # Reconstruction heads back to Layer-1 semantic & Layer-2 relational spaces
        self.w_rec_sem = (rng.standard_normal((self.hidden_dim, self.semantic_dim)) * scale).astype(np.float32)
        self.w_rec_rel = (rng.standard_normal((self.hidden_dim, self.semantic_dim)) * scale).astype(np.float32)

    def forward_glyph(self, glyph: TensorGlyph) -> ProjectedGlyphBundle:
        feats = extract_glyph_feature_bundle(
            glyph,
            semantic_dim=self.semantic_dim,
            rank=self.rank,
            geom_dim=self.geom_dim,
        )
        sem_h = feats["semantic_vec"] @ self.w_sem
        rel_u_h = feats["rel_u_pool"] @ self.w_rel_u
        rel_v_h = feats["rel_v_pool"] @ self.w_rel_v
        prov_h = 0.5 * (feats["geom_vec"] @ self.w_geom) + 0.5 * (feats["bloom_vec"] @ self.w_bloom)

        base_tokens = [sem_h, rel_u_h, rel_v_h, prov_h]
        soft_list: List[np.ndarray] = []
        for idx in range(self.num_soft_tokens):
            if idx < len(base_tokens):
                tok = base_tokens[idx] + self.slot_bias[idx]
            else:
                mix = 0.5 * sem_h + 0.25 * (rel_u_h + rel_v_h) + 0.25 * prov_h
                tok = mix + self.slot_bias[idx]
            soft_list.append(tok.astype(np.float32))

        soft_2d = np.stack(soft_list, axis=0)  # (k, hidden_dim)
        inputs_embeds = soft_2d[None, :, :]  # (1, k, hidden_dim)

        early_end = self.num_layers // 3
        mid_end = (2 * self.num_layers) // 3
        past_kv: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        bank_kv: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}

        for l_idx in range(self.num_layers):
            if l_idx < early_end:
                depth_signal = prov_h
            elif l_idx < mid_end:
                depth_signal = 0.5 * (rel_u_h + rel_v_h)
            else:
                depth_signal = sem_h

            conditioned = soft_2d + 0.25 * depth_signal[None, :]
            k_2d = (conditioned @ self.w_k_layers[l_idx]).astype(np.float32)
            v_2d = (conditioned @ self.w_v_layers[l_idx]).astype(np.float32)
            bank_kv[l_idx] = (k_2d, v_2d)

            # Reshape to (batch=1, num_heads, seq_len=k, head_dim)
            k_4d = k_2d.reshape(1, self.num_soft_tokens, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
            v_4d = v_2d.reshape(1, self.num_soft_tokens, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
            past_kv[l_idx] = (k_4d, v_4d)

        # Low-rank fast-weight adapter (A, B) in (1, hidden_dim, rank)
        fw_a = (self.w_rel_u.T @ feats["rel_u"])[None, :, :].astype(np.float32)
        fw_b = (self.w_rel_v.T @ feats["rel_v"])[None, :, :].astype(np.float32)

        pooled = soft_2d.mean(axis=0, keepdims=True)  # (1, hidden_dim)
        rec_sem = _l2_normalize(soft_2d[0] @ self.w_rec_sem)[None, :]
        rec_rel = _l2_normalize((0.5 * (soft_2d[1] + soft_2d[2]) if self.num_soft_tokens >= 3 else pooled[0]) @ self.w_rec_rel)[None, :]

        return ProjectedGlyphBundle(
            glyph_id=glyph.glyph_id,
            inputs_embeds=inputs_embeds,
            past_key_values=past_kv,
            kv_bank_slices=bank_kv,
            fast_weight_a=fw_a,
            fast_weight_b=fw_b,
            reconstructed_semantic=rec_sem,
            reconstructed_relational=rec_rel,
        )


class TorchMatrixGlyphProjector:
    """
    Horizon 2 Trainable Multi-Layer Tensor-Glyph Projector.

    Uses PyTorch `torch.nn.Module` with autograd when `torch` is installed (and `use_torch=True`),
    and provides a transparent pure-NumPy analytical twin (`NumpyMatrixGlyphTrainer`) so all tests
    and training scripts run deterministically with or without PyTorch.
    """

    def __init__(
        self,
        semantic_dim: int = 128,
        hidden_dim: int = 128,
        num_soft_tokens: int = 4,
        num_layers: int = 6,
        num_heads: int = 4,
        rank: int = 4,
        geom_dim: int = 22,
        seed: int = 42,
        use_torch: Optional[bool] = None,
    ) -> None:
        self.semantic_dim = int(semantic_dim)
        self.hidden_dim = int(hidden_dim)
        self.num_soft_tokens = max(2, int(num_soft_tokens))
        self.num_layers = max(3, int(num_layers))
        self.num_heads = max(1, int(num_heads))
        self.head_dim = self.hidden_dim // self.num_heads
        self.rank = max(1, int(rank))
        self.geom_dim = int(geom_dim)
        self.seed = int(seed)
        self.use_torch = HAS_TORCH if use_torch is None else (bool(use_torch) and HAS_TORCH)

        self.np_engine = NumpyMatrixGlyphTrainer(
            semantic_dim=self.semantic_dim,
            hidden_dim=self.hidden_dim,
            num_soft_tokens=self.num_soft_tokens,
            num_layers=self.num_layers,
            num_heads=self.num_heads,
            rank=self.rank,
            geom_dim=self.geom_dim,
            seed=self.seed,
        )
        self.torch_module: Any = None
        if self.use_torch:
            self.torch_module = self._build_torch_module()

    def _build_torch_module(self) -> Any:
        import torch
        import torch.nn as nn

        np_eng = self.np_engine

        class _ProjectorModule(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.w_sem = nn.Parameter(torch.from_numpy(np_eng.w_sem.copy()))
                self.w_rel_u = nn.Parameter(torch.from_numpy(np_eng.w_rel_u.copy()))
                self.w_rel_v = nn.Parameter(torch.from_numpy(np_eng.w_rel_v.copy()))
                self.w_geom = nn.Parameter(torch.from_numpy(np_eng.w_geom.copy()))
                self.w_bloom = nn.Parameter(torch.from_numpy(np_eng.w_bloom.copy()))
                self.slot_bias = nn.Parameter(torch.from_numpy(np_eng.slot_bias.copy()))
                self.w_k_layers = nn.ParameterList(
                    [nn.Parameter(torch.from_numpy(w.copy())) for w in np_eng.w_k_layers]
                )
                self.w_v_layers = nn.ParameterList(
                    [nn.Parameter(torch.from_numpy(w.copy())) for w in np_eng.w_v_layers]
                )
                self.w_rec_sem = nn.Parameter(torch.from_numpy(np_eng.w_rec_sem.copy()))
                self.w_rec_rel = nn.Parameter(torch.from_numpy(np_eng.w_rec_rel.copy()))

        return _ProjectorModule()

    def sync_torch_to_numpy(self) -> None:
        if self.torch_module is None:
            return
        m = self.torch_module
        self.np_engine.w_sem = m.w_sem.detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_rel_u = m.w_rel_u.detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_rel_v = m.w_rel_v.detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_geom = m.w_geom.detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_bloom = m.w_bloom.detach().cpu().numpy().astype(np.float32)
        self.np_engine.slot_bias = m.slot_bias.detach().cpu().numpy().astype(np.float32)
        for idx in range(self.num_layers):
            self.np_engine.w_k_layers[idx] = m.w_k_layers[idx].detach().cpu().numpy().astype(np.float32)
            self.np_engine.w_v_layers[idx] = m.w_v_layers[idx].detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_rec_sem = m.w_rec_sem.detach().cpu().numpy().astype(np.float32)
        self.np_engine.w_rec_rel = m.w_rec_rel.detach().cpu().numpy().astype(np.float32)

    def project(self, glyph: TensorGlyph) -> ProjectedGlyphBundle:
        """Project a TensorGlyph into continuous soft-token `inputs_embeds`, depth-specialized KV slices & fast weights."""
        if self.use_torch and self.torch_module is not None:
            self.sync_torch_to_numpy()
        return self.np_engine.forward_glyph(glyph)


class GlyphConditionedAttentionLM:
    """
    Causal Transformer Attention LM conditioned directly on continuous Matrix-Glyph
    `inputs_embeds` + `KVGlyphBank` `past_key_values` + low-rank fast-weight deltas `(A, B)`,
    requiring ZERO raw text tokens from the archived episode.
    """

    def __init__(
        self,
        vocab_size: int = 128,
        hidden_dim: int = 128,
        num_layers: int = 6,
        num_heads: int = 4,
        seed: int = 77,
    ) -> None:
        self.vocab_size = int(vocab_size)
        self.hidden_dim = int(hidden_dim)
        self.num_layers = int(num_layers)
        self.num_heads = int(num_heads)
        self.head_dim = self.hidden_dim // self.num_heads
        self.seed = int(seed)

        rng = np.random.default_rng(seed)
        scale = 1.0 / math.sqrt(self.hidden_dim)
        self.token_embed = (rng.standard_normal((self.vocab_size, self.hidden_dim)) * scale).astype(np.float32)
        self.w_q = _deterministic_orth_matrix(self.hidden_dim, self.hidden_dim, seed + 1)
        self.w_o = _deterministic_orth_matrix(self.hidden_dim, self.hidden_dim, seed + 2)
        self.lm_head = (rng.standard_normal((self.hidden_dim, self.vocab_size)) * scale).astype(np.float32)

    def forward(
        self,
        bundle: ProjectedGlyphBundle,
        query_token_ids: Sequence[int],
        extra_kv_bank: Optional[KVGlyphBank] = None,
    ) -> Dict[str, Any]:
        """
        Run multi-layer attention over `[kv_bank_prefix || soft_tokens || active_query_tokens]`
        with zero tokenized archived text.
        """
        q_ids = [int(t) % self.vocab_size for t in query_token_ids]
        if not q_ids:
            q_ids = [0]
        q_embeds = self.token_embed[q_ids]  # (seq_len, hidden_dim)
        soft_2d = bundle.inputs_embeds[0]  # (k, hidden_dim)

        h = q_embeds.copy()
        attn_weights_per_layer: List[np.ndarray] = []

        for l_idx in range(self.num_layers):
            k_glyph, v_glyph = bundle.kv_bank_slices[l_idx]  # (k, hidden_dim)
            k_parts = [k_glyph]
            v_parts = [v_glyph]

            if extra_kv_bank is not None:
                for slot in extra_kv_bank._slots:
                    if slot is not None and slot.glyph_id != bundle.glyph_id and l_idx in slot.kv_slices:
                        kb, vb = slot.kv_slices[l_idx]
                        k_parts.insert(0, kb)
                        v_parts.insert(0, vb)

            # Query tokens also attend to soft_2d and themselves causally
            k_all = np.concatenate(k_parts + [soft_2d, h], axis=0)  # (total_ctx, hidden_dim)
            v_all = np.concatenate(v_parts + [soft_2d, h], axis=0)

            q_proj = h @ self.w_q  # (seq_len, hidden_dim)
            scores = (q_proj @ k_all.T) / math.sqrt(self.hidden_dim)
            scores = scores - scores.max(axis=-1, keepdims=True)
            probs = np.exp(scores)
            probs = probs / np.maximum(probs.sum(axis=-1, keepdims=True), 1e-9)
            attn_weights_per_layer.append(probs.astype(np.float32))

            ctx = (probs @ v_all) @ self.w_o
            h = h + 0.25 * ctx

        # Apply Layer-2 low-rank fast-weight delta (A, B)
        fw_a = bundle.fast_weight_a[0]  # (hidden_dim, rank)
        fw_b = bundle.fast_weight_b[0]  # (hidden_dim, rank)
        h = h + 0.15 * ((h @ fw_b) @ fw_a.T)

        # Condition final token representation on pooled soft-token prefix so soft tokens steer next-token prediction
        prefix_ctx = soft_2d.mean(axis=0, keepdims=True)  # (1, hidden_dim)
        conditioned_h = h + prefix_ctx
        logits = (conditioned_h @ self.lm_head).astype(np.float32)  # (seq_len, vocab_size)

        return {
            "logits": logits,
            "hidden_states": conditioned_h,
            "attention_weights": attn_weights_per_layer,
            "archived_text_tokens_used": 0,
            "soft_prefix_tokens_used": int(soft_2d.shape[0]),
        }


def _cross_entropy_and_grad(logits: np.ndarray, targets: Sequence[int]) -> Tuple[float, np.ndarray]:
    """Compute mean token cross-entropy loss and d(loss)/d(logits)."""
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp_l = np.exp(shifted)
    probs = exp_l / np.maximum(exp_l.sum(axis=-1, keepdims=True), 1e-12)
    n = len(targets)
    loss = 0.0
    grad = probs.copy()
    for i, t in enumerate(targets):
        idx = int(t) % logits.shape[1]
        p = float(max(probs[i, idx], 1e-12))
        loss -= math.log(p)
        grad[i, idx] -= 1.0
    return loss / max(1, n), (grad / max(1, n)).astype(np.float32)


def train_projector_on_glyphs(
    glyphs: Sequence[TensorGlyph],
    target_token_sequences: Optional[Sequence[Sequence[int]]] = None,
    epochs: int = 35,
    lr: float = 0.08,
    hidden_dim: int = 128,
    num_soft_tokens: int = 4,
    num_layers: int = 6,
    num_heads: int = 4,
    vocab_size: int = 128,
    prefer_torch: bool = True,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Train `TorchMatrixGlyphProjector` + `GlyphConditionedAttentionLM` on compiled TensorGlyphs
    using ONLY continuous Matrix-Glyph soft tokens & KV slices (`0` raw archived text tokens).

    Optimizes joint loss:
      L = L_ce (continuation token cross-entropy)
        + L_sem (1 - cosine(reconstructed_semantic, target_semantic))
        + L_rel (1 - cosine(reconstructed_relational, target_relational))
    """
    if not glyphs:
        raise ValueError("train_projector_on_glyphs requires at least 1 TensorGlyph")

    sem_dim = int(glyphs[0].semantic.vector.shape[0])
    rank = int(glyphs[0].relational.rank)
    use_torch = bool(prefer_torch and HAS_TORCH)

    projector = TorchMatrixGlyphProjector(
        semantic_dim=sem_dim,
        hidden_dim=hidden_dim,
        num_soft_tokens=num_soft_tokens,
        num_layers=num_layers,
        num_heads=num_heads,
        rank=rank,
        seed=seed,
        use_torch=use_torch,
    )
    lm = GlyphConditionedAttentionLM(
        vocab_size=vocab_size,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        num_heads=num_heads,
        seed=seed + 100,
    )

    # Deterministic target continuation tokens derived from each glyph's live slots & keywords if not supplied
    targets_list: List[List[int]] = []
    queries_list: List[List[int]] = []
    for idx, g in enumerate(glyphs):
        if target_token_sequences and idx < len(target_token_sequences):
            t_seq = [int(x) % vocab_size for x in target_token_sequences[idx]]
        else:
            digest_bytes = bytes.fromhex(g.content_digest()[:16])
            t_seq = [int(b) % vocab_size for b in digest_bytes[:6]]
        q_seq = [(t + 17) % vocab_size for t in t_seq]
        targets_list.append(t_seq)
        queries_list.append(q_seq)

    loss_history: List[Dict[str, float]] = []

    if use_torch and projector.torch_module is not None:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F

        m = projector.torch_module
        t_embed = nn.Parameter(torch.from_numpy(lm.token_embed.copy()))
        t_lm_head = nn.Parameter(torch.from_numpy(lm.lm_head.copy()))
        t_wq = torch.from_numpy(lm.w_q.copy())
        t_wo = torch.from_numpy(lm.w_o.copy())

        params = list(m.parameters()) + [t_embed, t_lm_head]
        optimizer = torch.optim.Adam(params, lr=lr * 0.35)

        feat_bundles = [
            extract_glyph_feature_bundle(g, semantic_dim=sem_dim, rank=rank)
            for g in glyphs
        ]

        for ep in range(epochs + 1):
            total_ce = 0.0
            total_sem_cos = 0.0
            total_rel_cos = 0.0

            if ep > 0:
                optimizer.zero_grad()

            batch_loss = torch.tensor(0.0, dtype=torch.float32)
            for idx, feats in enumerate(feat_bundles):
                sem_v = torch.from_numpy(feats["semantic_vec"])
                rel_u_p = torch.from_numpy(feats["rel_u_pool"])
                rel_v_p = torch.from_numpy(feats["rel_v_pool"])
                geom_v = torch.from_numpy(feats["geom_vec"])
                bloom_v = torch.from_numpy(feats["bloom_vec"])
                rel_u_mat = torch.from_numpy(feats["rel_u"])
                rel_v_mat = torch.from_numpy(feats["rel_v"])

                sem_h = sem_v @ m.w_sem
                rel_u_h = rel_u_p @ m.w_rel_u
                rel_v_h = rel_v_p @ m.w_rel_v
                prov_h = 0.5 * (geom_v @ m.w_geom) + 0.5 * (bloom_v @ m.w_bloom)

                base_toks = [sem_h, rel_u_h, rel_v_h, prov_h]
                soft_toks = []
                for s_i in range(projector.num_soft_tokens):
                    b_tok = base_toks[s_i] if s_i < len(base_toks) else (0.5 * sem_h + 0.25 * (rel_u_h + rel_v_h) + 0.25 * prov_h)
                    soft_toks.append(b_tok + m.slot_bias[s_i])
                soft_2d = torch.stack(soft_toks, dim=0)  # (k, hidden_dim)

                # Reconstruct semantic & relational targets
                rec_sem = F.normalize(soft_2d[0] @ m.w_rec_sem, dim=0)
                rec_rel = F.normalize((0.5 * (soft_2d[1] + soft_2d[2])) @ m.w_rec_rel, dim=0)
                target_rel = F.normalize(0.5 * (rel_u_p + rel_v_p), dim=0)

                sem_cos = torch.sum(rec_sem * sem_v)
                rel_cos = torch.sum(rec_rel * target_rel)

                # Attention LM forward conditioned on depth-specialized KV slices + soft prefix
                q_ids_t = torch.tensor(queries_list[idx], dtype=torch.long)
                t_ids_t = torch.tensor(targets_list[idx], dtype=torch.long)
                h = t_embed[q_ids_t]

                early_end = projector.num_layers // 3
                mid_end = (2 * projector.num_layers) // 3
                for l_idx in range(projector.num_layers):
                    d_sig = prov_h if l_idx < early_end else ((0.5 * (rel_u_h + rel_v_h)) if l_idx < mid_end else sem_h)
                    cond = soft_2d + 0.25 * d_sig.unsqueeze(0)
                    k_2d = cond @ m.w_k_layers[l_idx]
                    v_2d = cond @ m.w_v_layers[l_idx]
                    k_all = torch.cat([k_2d, soft_2d, h], dim=0)
                    v_all = torch.cat([v_2d, soft_2d, h], dim=0)
                    scores = ((h @ t_wq) @ k_all.T) / math.sqrt(hidden_dim)
                    probs = torch.softmax(scores, dim=-1)
                    h = h + 0.25 * ((probs @ v_all) @ t_wo)

                fw_a = m.w_rel_u.T @ rel_u_mat
                fw_b = m.w_rel_v.T @ rel_v_mat
                h = h + 0.15 * ((h @ fw_b) @ fw_a.T)
                cond_h = h + soft_2d.mean(dim=0, keepdim=True)
                logits = cond_h @ t_lm_head

                ce_loss = F.cross_entropy(logits, t_ids_t)
                loss_i = ce_loss + 1.5 * (1.0 - sem_cos) + 1.5 * (1.0 - rel_cos)
                batch_loss = batch_loss + loss_i

                total_ce += float(ce_loss.item())
                total_sem_cos += float(sem_cos.item())
                total_rel_cos += float(rel_cos.item())

            batch_loss = batch_loss / len(feat_bundles)
            if ep > 0:
                batch_loss.backward()
                optimizer.step()

            n_g = len(feat_bundles)
            mean_ce = total_ce / n_g
            mean_sem = total_sem_cos / n_g
            mean_rel = total_rel_cos / n_g
            loss_history.append(
                {
                    "epoch": float(ep),
                    "total_loss": round(float(batch_loss.item()), 4),
                    "ce_loss": round(mean_ce, 4),
                    "perplexity": round(math.exp(min(20.0, mean_ce)), 4),
                    "semantic_cosine": round(mean_sem, 4),
                    "relational_cosine": round(mean_rel, 4),
                }
            )

        projector.sync_torch_to_numpy()
        lm.token_embed = t_embed.detach().cpu().numpy().astype(np.float32)
        lm.lm_head = t_lm_head.detach().cpu().numpy().astype(np.float32)
        backend_used = "pytorch"
    else:
        # Pure-NumPy analytical gradient descent twin
        np_eng = projector.np_engine
        feat_bundles = [
            extract_glyph_feature_bundle(g, semantic_dim=sem_dim, rank=rank)
            for g in glyphs
        ]

        for ep in range(epochs + 1):
            total_ce = 0.0
            total_sem_cos = 0.0
            total_rel_cos = 0.0

            for idx, (g, feats) in enumerate(zip(glyphs, feat_bundles)):
                bundle = np_eng.forward_glyph(g)
                fw_out = lm.forward(bundle, queries_list[idx])
                logits = fw_out["logits"]
                ce_loss, d_logits = _cross_entropy_and_grad(logits, targets_list[idx])

                sem_target = feats["semantic_vec"]
                rel_target = _l2_normalize(0.5 * (feats["rel_u_pool"] + feats["rel_v_pool"]))
                rec_sem = bundle.reconstructed_semantic[0]
                rec_rel = bundle.reconstructed_relational[0]

                sem_cos = float(np.dot(rec_sem, sem_target))
                rel_cos = float(np.dot(rec_rel, rel_target))

                total_ce += ce_loss
                total_sem_cos += sem_cos
                total_rel_cos += rel_cos

                if ep < epochs:
                    # Analytical parameter updates for CE loss and semantic/relational reconstruction
                    cond_h = fw_out["hidden_states"]  # (seq, hidden_dim)
                    grad_lm_head = cond_h.T @ d_logits
                    grad_h = d_logits @ lm.lm_head.T  # (seq, hidden_dim)
                    lm.lm_head -= (lr * grad_lm_head).astype(np.float32)

                    for tok_pos, q_tok in enumerate(queries_list[idx]):
                        lm.token_embed[q_tok] -= (lr * 0.5 * grad_h[tok_pos]).astype(np.float32)

                    grad_prefix = grad_h.mean(axis=0)  # (hidden_dim,)
                    np_eng.slot_bias -= (lr * 0.3 * grad_prefix[None, :]).astype(np.float32)

                    # Cosine reconstruction analytical updates: align w_sem, w_rec_sem, w_rel_u, w_rec_rel
                    soft0 = _l2_normalize(feats["semantic_vec"] @ np_eng.w_sem + np_eng.slot_bias[0])
                    err_sem = sem_target - rec_sem
                    np_eng.w_rec_sem += (lr * 1.4 * np.outer(soft0, err_sem)).astype(np.float32)
                    np_eng.w_sem += (lr * 0.8 * np.outer(feats["semantic_vec"], err_sem @ np_eng.w_rec_sem.T)).astype(np.float32)

                    soft_rel = _l2_normalize(0.5 * (feats["rel_u_pool"] @ np_eng.w_rel_u + feats["rel_v_pool"] @ np_eng.w_rel_v))
                    err_rel = rel_target - rec_rel
                    np_eng.w_rec_rel += (lr * 1.4 * np.outer(soft_rel, err_rel)).astype(np.float32)
                    np_eng.w_rel_u += (lr * 0.6 * np.outer(feats["rel_u_pool"], err_rel @ np_eng.w_rec_rel.T)).astype(np.float32)
                    np_eng.w_rel_v += (lr * 0.6 * np.outer(feats["rel_v_pool"], err_rel @ np_eng.w_rec_rel.T)).astype(np.float32)

            n_g = len(glyphs)
            mean_ce = total_ce / n_g
            mean_sem = total_sem_cos / n_g
            mean_rel = total_rel_cos / n_g
            tot_l = mean_ce + 1.5 * (1.0 - mean_sem) + 1.5 * (1.0 - mean_rel)
            loss_history.append(
                {
                    "epoch": float(ep),
                    "total_loss": round(tot_l, 4),
                    "ce_loss": round(mean_ce, 4),
                    "perplexity": round(math.exp(min(20.0, mean_ce)), 4),
                    "semantic_cosine": round(mean_sem, 4),
                    "relational_cosine": round(mean_rel, 4),
                }
            )
        backend_used = "numpy"

    # Verify KVGlyphBank prefix byte-invariance when appending projected KV slices sequentially
    kv_bank = KVGlyphBank(num_layers=num_layers, max_slots=max(16, len(glyphs) + 4))
    prefix_invariance_ok = True
    prev_fp = b""
    for idx, g in enumerate(glyphs):
        b_out = projector.project(g)
        kv_bank.allocate_slot(g, b_out.kv_bank_slices)
        if idx > 0:
            check_fp = kv_bank.prefix_bytes_prefix_hash(idx)
            if check_fp != prev_fp:
                prefix_invariance_ok = False
        prev_fp = kv_bank.prefix_bytes_prefix_hash(idx + 1)

    raw_tokens = sum(max(1, g.provenance.raw_token_count) for g in glyphs)
    soft_tokens = len(glyphs) * projector.num_soft_tokens
    initial = loss_history[0]
    final = loss_history[-1]

    return {
        "backend": backend_used,
        "epochs": epochs,
        "glyph_count": len(glyphs),
        "num_soft_tokens_per_glyph": projector.num_soft_tokens,
        "raw_archived_tokens": raw_tokens,
        "injected_soft_tokens": soft_tokens,
        "archived_text_tokens_tokenized": 0,
        "sequence_compression_factor": round(raw_tokens / float(max(1, soft_tokens)), 2),
        "initial_total_loss": initial["total_loss"],
        "final_total_loss": final["total_loss"],
        "initial_ce_loss": initial["ce_loss"],
        "final_ce_loss": final["ce_loss"],
        "initial_perplexity": initial["perplexity"],
        "final_perplexity": final["perplexity"],
        "perplexity_reduction_ratio": round(initial["perplexity"] / max(1e-6, final["perplexity"]), 2),
        "initial_semantic_cosine": initial["semantic_cosine"],
        "final_semantic_cosine": final["semantic_cosine"],
        "initial_relational_cosine": initial["relational_cosine"],
        "final_relational_cosine": final["relational_cosine"],
        "kv_prefix_byte_invariance": prefix_invariance_ok,
        "kv_append_preservation_ratio": kv_bank.append_preservation_ratio(),
        "loss_history": loss_history,
        "projector": projector,
        "lm": lm,
    }
