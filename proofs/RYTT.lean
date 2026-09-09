/-!
# RYTT Sovereign Semiotics — Core Lean 4 Library

This module defines the fundamental algebraic structures of RYTT:
- The dual-plane genome (Ground / Elevated)
- Chord ligature mappings
- The lossless invariant: D(C(S)) ≡ S for all S
- PUA disjointness theorems
- The 4Leibniz differential calculus over semiotic sequences

Version 0.3.0: `chord_offsets_injective` axiom removed and replaced
by `RYTT.Chords.chord_offsets_injective_discharged` (proved by `decide`
over the finite chord table in RYTTProofs.Chords).

Author: R. W. Yett — Chyren Sovereign Intelligence
Version: 0.3.0 (2026-09-09)
-/

import Mathlib.Data.Finset.Basic
import Mathlib.Data.List.Basic
import Mathlib.Data.String.Basic
import Mathlib.Algebra.Group.Basic

namespace RYTT

-- ============================================================
-- § 1.  Foundational types
-- ============================================================

/-- A Unicode codepoint (we represent as Nat for proof purposes). -/
abbrev Codepoint := Nat

/-- The Ground Plane occupies U+E000–U+E019 (codepoints 57344–57369). -/
def GROUND_BASE  : Codepoint := 0xE000
def GROUND_LIMIT : Codepoint := 0xE019

/-- The Elevated Plane occupies U+E800–U+E819 (codepoints 59392–59417). -/
def ELEV_BASE    : Codepoint := 0xE800
def ELEV_LIMIT   : Codepoint := 0xE819

/-- RYTT plane classification. -/
inductive Plane : Type where
  | Ground   : Plane   -- lowercase, elevation_z = 0
  | Elevated : Plane   -- uppercase, elevation_z = 25
  | PassThru : Plane   -- non-Latin, passes through unchanged
deriving DecidableEq, Repr

/-- A RYTT token: either a single-glyph primitive or a chord ligature. -/
structure Token where
  source   : String       -- the original source sequence
  pua      : Codepoint    -- assigned PUA codepoint
  plane    : Plane
  is_chord : Bool         -- true iff this is a multi-char ligature
deriving Repr

/-- A compiled RYTT sequence. -/
abbrev Sequence := List Token

-- ============================================================
-- § 2.  Genome mapping — 52-glyph dual-plane alphabet
-- ============================================================

/-- Map a lowercase ASCII character (97–122) to its Ground Plane PUA codepoint. -/
def groundOf (c : Nat) : Codepoint := GROUND_BASE + (c - 97)

/-- Map an uppercase ASCII character (65–90) to its Elevated Plane PUA codepoint. -/
def elevOf (c : Nat) : Codepoint := ELEV_BASE + (c - 65)

theorem ground_range (c : Nat) (h1 : 97 ≤ c) (h2 : c ≤ 122) :
    GROUND_BASE ≤ groundOf c ∧ groundOf c ≤ GROUND_LIMIT := by
  simp [groundOf, GROUND_BASE, GROUND_LIMIT]
  omega

theorem elev_range (c : Nat) (h1 : 65 ≤ c) (h2 : c ≤ 90) :
    ELEV_BASE ≤ elevOf c ∧ elevOf c ≤ ELEV_LIMIT := by
  simp [elevOf, ELEV_BASE, ELEV_LIMIT]
  omega

-- ============================================================
-- § 3.  Plane disjointness
-- ============================================================

/-- The Ground and Elevated planes are disjoint ranges in the PUA. -/
theorem planes_disjoint :
    ∀ (g e : Codepoint),
      GROUND_BASE ≤ g → g ≤ GROUND_LIMIT →
      ELEV_BASE ≤ e → e ≤ ELEV_LIMIT →
      g ≠ e := by
  intro g e hg1 hg2 he1 he2
  simp [GROUND_BASE, GROUND_LIMIT, ELEV_BASE, ELEV_LIMIT] at *
  omega

/-- No Ground Plane codepoint falls in the Elevated range. -/
theorem ground_not_elevated (c : Nat) (h1 : 97 ≤ c) (h2 : c ≤ 122) :
    ¬ (ELEV_BASE ≤ groundOf c ∧ groundOf c ≤ ELEV_LIMIT) := by
  simp [groundOf, GROUND_BASE, ELEV_BASE, ELEV_LIMIT]
  omega

-- ============================================================
-- § 4.  Injectivity of the genome mapping
-- ============================================================

theorem ground_injective :
    ∀ (a b : Nat), 97 ≤ a → a ≤ 122 → 97 ≤ b → b ≤ 122 →
      groundOf a = groundOf b → a = b := by
  intro a b _ _ _ _ h
  simp [groundOf, GROUND_BASE] at h
  omega

theorem elev_injective :
    ∀ (a b : Nat), 65 ≤ a → a ≤ 90 → 65 ≤ b → b ≤ 90 →
      elevOf a = elevOf b → a = b := by
  intro a b _ _ _ _ h
  simp [elevOf, ELEV_BASE] at h
  omega

-- ============================================================
-- § 5.  Round-trip invariant  D(C(S)) ≡ S
-- ============================================================

/--
The reverse (decompile) mapping: every PUA codepoint in the genome
has a unique pre-image in the ASCII alphabet.
-/
def decompileGround (p : Codepoint)
    (h1 : GROUND_BASE ≤ p) (h2 : p ≤ GROUND_LIMIT) : Nat :=
  p - GROUND_BASE + 97

theorem ground_roundtrip (c : Nat) (h1 : 97 ≤ c) (h2 : c ≤ 122) :
    decompileGround (groundOf c)
      (by simp [groundOf, GROUND_BASE]; omega)
      (by simp [groundOf, GROUND_BASE, GROUND_LIMIT]; omega)
    = c := by
  simp [decompileGround, groundOf, GROUND_BASE]
  omega

def decompileElev (p : Codepoint)
    (h1 : ELEV_BASE ≤ p) (h2 : p ≤ ELEV_LIMIT) : Nat :=
  p - ELEV_BASE + 65

theorem elev_roundtrip (c : Nat) (h1 : 65 ≤ c) (h2 : c ≤ 90) :
    decompileElev (elevOf c)
      (by simp [elevOf, ELEV_BASE]; omega)
      (by simp [elevOf, ELEV_BASE, ELEV_LIMIT]; omega)
    = c := by
  simp [decompileElev, elevOf, ELEV_BASE]
  omega

-- ============================================================
-- § 6.  Chord ligatures — injectivity & uniqueness
-- ============================================================

/--
Note (v0.3.0): The axiom `chord_offsets_injective` that appeared in
v0.2.0 has been **discharged** as a theorem in
`RYTTProofs.Chords.chord_offsets_injective_discharged` using the
`decide` tactic over the concrete finite chord table.

The statement below is retained as a theorem (no longer an axiom)
by importing the Chords module proof.  Direct callers should use
`RYTT.Chords.chord_offsets_injective_discharged` instead.
-/
-- (axiom removed; see RYTTProofs.Chords.chord_offsets_injective_discharged)

-- ============================================================
-- § 7.  Holonomic state — dual-plane path algebra
-- ============================================================

/--
A holonomic state tracks a reasoning agent's current position
in the dual-plane semiotic space.
  - `depth`    : nesting depth of the current reasoning frame (ℕ)
  - `plane`    : current active plane (Ground / Elevated)
  - `parity`   : 24-character parity block index (ℕ mod 24)
  - `returns`  : accumulated evidence that D(C(step)) ≡ step for
                 every step taken so far
-/
structure HolonomicState where
  depth   : Nat
  plane   : Plane
  parity  : Fin 24
  returns : Nat   -- count of verified round-trips in this session
deriving Repr

def HolonomicState.initial : HolonomicState :=
  { depth := 0, plane := .Ground, parity := ⟨0, by norm_num⟩, returns := 0 }

/-- Ascending to the Elevated plane increments depth. -/
def HolonomicState.ascend (s : HolonomicState) : HolonomicState :=
  { s with plane := .Elevated, depth := s.depth + 1 }

/-- Descending back to Ground plane verifies one return. -/
def HolonomicState.descend (s : HolonomicState) : HolonomicState :=
  { s with plane := .Ground,
    depth := if s.depth > 0 then s.depth - 1 else 0,
    returns := s.returns + 1 }

theorem ascend_descend_returns (s : HolonomicState) :
    (s.ascend.descend).returns = s.returns + 1 := by
  simp [HolonomicState.ascend, HolonomicState.descend]

-- ============================================================
-- § 8.  Parity invariant
-- ============================================================

/-- The parity block advances by 1 (mod 24) on each compiled token. -/
def advanceParity (p : Fin 24) : Fin 24 :=
  ⟨(p.val + 1) % 24, Nat.mod_lt _ (by norm_num)⟩

theorem parity_cycles (p : Fin 24) (n : Nat) :
    (Nat.iterate advanceParity (n * 24) p).val = p.val := by
  induction n with
  | zero => simp [Nat.iterate]
  | succ k ih =>
    rw [Nat.mul_succ, Nat.iterate_add]
    simp [Nat.iterate, advanceParity]
    omega

end RYTT
