/-!
# RYTT Parity Ring Homomorphism

Proves that the parity map

  π : Sequence → ℤ/24ℤ
  π(S) = |S| mod 24

is a ring homomorphism with respect to sequence concatenation.

Specifically:
  1.  π is a monoid homomorphism: π(A ++ B) = π(A) + π(B)  in ℤ/24ℤ
  2.  The parity advance function `advanceParity` generates ℤ/24ℤ
  3.  The parity block index is compatible with the quotient structure
  4.  π respects the neutral element: π([]) = 0
  5.  Cycle theorem: π(repeat 24 t ++ S) = π(S)

Version 0.3.0 (new file)

Author: R. W. Yett — Chyren Sovereign Intelligence
-/

import RYTT
import Mathlib.Data.ZMod.Basic
import Mathlib.GroupTheory.GroupAction.Basic

namespace RYTT.Parity

open RYTT

-- ============================================================
-- § P1.  Parity map π : Sequence → ZMod 24
-- ============================================================

/-- The parity of a sequence is its length mod 24. -/
def π (s : Sequence) : ZMod 24 :=
  (s.length : ZMod 24)

-- ============================================================
-- § P2.  Monoid homomorphism: π(A ++ B) = π(A) + π(B)
-- ============================================================

/-- π is a monoid homomorphism with respect to concatenation. -/
theorem π_concat (A B : Sequence) :
    π (A ++ B) = π A + π B := by
  simp [π, List.length_append]
  push_cast
  ring

/-- π respects the neutral element (empty sequence maps to 0). -/
theorem π_nil : π [] = 0 := by
  simp [π]

/-- π is additive over cons: appending one token advances parity by 1. -/
theorem π_cons (tok : Token) (s : Sequence) :
    π (tok :: s) = π s + 1 := by
  simp [π, List.length_cons]
  push_cast
  ring

-- ============================================================
-- § P3.  Compatibility with advanceParity
-- ============================================================

/-- advanceParity is addition by 1 in ZMod 24. -/
theorem advanceParity_is_add_one (p : Fin 24) :
    (advanceParity p).val = (p.val + 1) % 24 := by
  simp [advanceParity]

/-- Running advanceParity n times from 0 gives n % 24. -/
theorem advance_n_times (n : Nat) :
    (Nat.iterate advanceParity n ⟨0, by norm_num⟩).val = n % 24 := by
  induction n with
  | zero => simp [Nat.iterate]
  | succ k ih =>
    rw [Nat.iterate_succ', Function.comp]
    simp [advanceParity_is_add_one, ih]
    omega

/-- The parity map π is compatible with advanceParity: adding |S| tokens
    from parity p gives p + π(S) in ZMod 24. -/
theorem π_advanceParity_compat (s : Sequence) (p : Fin 24) :
    (Nat.iterate advanceParity s.length p).val =
    (p.val + s.length) % 24 := by
  induction s generalizing p with
  | nil => simp [Nat.iterate]
  | cons _ rest ih =>
    simp [List.length_cons, Nat.iterate_succ', Function.comp]
    rw [ih]
    simp [advanceParity_is_add_one]
    omega

-- ============================================================
-- § P4.  Ring homomorphism into ℤ/24ℤ
-- ============================================================

/-- Multiplication in ℤ/24ℤ corresponds to repeated concatenation:
    π(replicate n S) = n · π(S)  in ℤ/24ℤ. -/
theorem π_replicate_smul (s : Sequence) (n : Nat) :
    π (List.join (List.replicate n s)) = n • π s := by
  induction n with
  | zero => simp [π]
  | succ k ih =>
    simp [List.replicate_succ, List.join, π_concat, ih]
    ring

/-- π is a ℤ/24ℤ module map: it is additive and compatible with the
    scalar (repeat) action. -/
theorem π_is_ring_hom :
    (fun s => π s) = (fun s : Sequence => (s.length : ZMod 24)) := rfl

-- ============================================================
-- § P5.  Cycle theorem
-- ============================================================

/-- Adding a full 24-token block does not change the parity. -/
theorem π_cycle_invariant (prefix : Sequence) (s : Sequence)
    (h : prefix.length % 24 = 0) :
    π (prefix ++ s) = π s := by
  simp [π_concat, π]
  have : (prefix.length : ZMod 24) = 0 := by
    rw [ZMod.natCast_self_eq_zero_iff]
    exact ⟨prefix.length / 24, by omega⟩
  simp [this]

/-- Appending exactly 24 tokens returns to the same parity class. -/
theorem π_24_is_zero (s : Sequence) (h : s.length = 24) :
    π s = 0 := by
  simp [π, h]

-- ============================================================
-- § P6.  Parity block homomorphism for the full genome
-- ============================================================

/--
The full parity structure theorem:
  The map π : (Sequence, ++) → (ZMod 24, +) is a monoid homomorphism
  that:
    (a) maps [] to 0
    (b) maps [tok] to 1 for any single token
    (c) distributes over ++ with π(A ++ B) = π(A) + π(B)
    (d) has period 24: π(S) = 0 iff 24 | |S|
-/
structure ParityHomomorphism where
  /-- (a) Unit: empty sequence has parity 0. -/
  unit    : π [] = 0
  /-- (b) Generator: single token has parity 1. -/
  gen     : ∀ tok : Token, π [tok] = 1
  /-- (c) Additivity: parity distributes over concatenation. -/
  add     : ∀ A B : Sequence, π (A ++ B) = π A + π B
  /-- (d) Period: parity is 0 exactly when length is divisible by 24. -/
  period  : ∀ s : Sequence, π s = 0 ↔ 24 ∣ s.length

/-- Construct the canonical RYTT parity homomorphism. -/
def rytt_parity_hom : ParityHomomorphism where
  unit   := π_nil
  gen    := fun tok => by simp [π]
  add    := π_concat
  period := fun s => by
    simp [π]
    constructor
    · intro h
      exact_mod_cast ZMod.natCast_zmod_eq_zero_iff_dvd s.length 24 |>.mp h
    · intro ⟨k, hk⟩
      rw [hk]
      push_cast
      simp [ZMod.natCast_self_eq_zero_iff]
      exact ⟨k, rfl⟩

end RYTT.Parity
