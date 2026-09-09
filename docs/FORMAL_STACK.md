# RYTT Formal Stack — Complete Reference

## Overview

The RYTT formal stack is a four-layer architecture where each layer is
verified against the layer below it, with the Lean 4 proof system as
the ultimate ground truth.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4:  4Leibniz differential calculus                       │
│            δ_G · δ_E · δ_C · δ_P over RYTT sequences          │
│            proofs/RYTTProofs/Leibniz.lean                       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3:  VSA hypervector algebra                              │
│            bind ⊗ · superpose ⊕̄ · unbind · role-filler        │
│            proofs/RYTTProofs/VSA.lean  +  src/rytt/vsa.py       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2:  Chord injectivity + plane disjointness               │
│            All 23 chords provably unique within each plane      │
│            proofs/RYTTProofs/Chords.lean                        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1:  Round-trip invariant  D(C(S)) ≡ S                   │
│            Proved for all ASCII chars; full compiler induction  │
│            tracked in proofs/RYTTProofs/TODO.md                 │
│            proofs/RYTT.lean                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Round-trip invariant

**Theorem**: For any lowercase character `c` (97–122),
`decompileGround(groundOf(c)) = c`.
Same for uppercase via `decompileElev(elevOf(c)) = c`.

**Proved**: ✅ `proofs/RYTT.lean` § 5

**Pending**: Full structural induction over the greedy tokeniser loop.
See `proofs/RYTTProofs/TODO.md`.

---

## Layer 2 — Plane disjointness & chord injectivity

**Theorem**: Ground ∩ Elevated = ∅ in the PUA range.  
**Proved**: ✅ `planes_disjoint` in `RYTT.lean` § 3

**Theorem**: Within each plane, distinct chord sources have distinct offsets.  
**Proved**: ✅ `chord_table_no_dup_lower` / `chord_table_no_dup_upper`  
in `RYTTProofs/Chords.lean` via `decide`.

---

## Layer 3 — VSA hypervector algebra

**Theorem (unbind)**: `a ⊗ (a ⊗ b) = b` for all `a b : HV`.  
**Proved**: ✅ `unbind` in `RYTTProofs/VSA.lean` § V2

**Theorem (role-filler roundtrip)**: `decode(encode(rf)) = rf.filler`.  
**Proved**: ✅ `role_filler_roundtrip` in `VSA.lean` § V4

**Theorem (single-token retrieval)**: VSA retrieval is exact for single-entry records.  
**Proved**: ✅ `vsa_single_token_retrieval` in `VSA.lean` § V5

**Python implementation**: `src/rytt/vsa.py` — 10 240-bit BSC vectors,
numpy uint64 packing, SHA-512 deterministic seeding.

---

## Layer 4 — 4Leibniz differential calculus

Four differential operators over RYTT sequences:

| Operator | Symbol | Effect |
|---|---|---|
| Ground differential | δ_G | Sensitivity to lowercase perturbation |
| Elevated differential | δ_E | Sensitivity to uppercase / casing lift |
| Chord differential | δ_C | Sensitivity to chord boundary shift |
| Parity differential | δ_P | Fires at every 24th token (parity block) |

**Key theorems proved**:
- `delta_G_ground_is_zero`: δ_G on a Ground token = zero differential ✅
- `delta_E_delta_G_involution`: lifting then lowering returns original PUA ✅  
- `product_rule_ground`: Leibniz product rule for Ground differential ✅
- `parity_event_at_multiples`: δ_P fires at every n×24 tokens ✅
- `integrate_empty`: ∫(∅) = identity ✅
- `integrate_noop_diffs`: ∫(no-op diffs) = identity ✅

---

## AI Integration Layer

| Module | File | Purpose |
|---|---|---|
| `MemoryEncoder` | `src/rytt/integration.py` | RYTT+VSA episodic memory |
| `ChainOfThoughtEncoder` | `src/rytt/integration.py` | Holonomic CoT with audit trail |
| `SemanticAnnotator` | `src/rytt/integration.py` | Dual-channel plane annotation |
| `HolonomicVSATracker` | `src/rytt/vsa.py` | Live VSA state tracker |
| `HolonomicState` | `src/rytt/holonomic.py` | Plane-transition audit state |

---

## Running the Lean proofs

```bash
cd proofs
lake update
lake build
lake exe rytt_check
```

Requires Lean 4 (v4.x) and Mathlib4.  See `proofs/lakefile.lean`.

---

## Research citations

This formal stack draws on:
- **VSA/HDC**: Kanerva (2009), Plate (1995), Frady et al. (2021)
- **Lean 4**: de Moura et al. (2021)
- **Holonomic sequences**: Zeilberger (1990), Chyzak (1998)
- **4Leibniz**: Original contribution — R. W. Yett (2026)
- **Dual-plane semiotic geometry**: Original contribution — R. W. Yett (2026)
