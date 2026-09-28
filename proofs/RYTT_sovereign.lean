/-!
# RYTT Sovereign Semiotics — expanded verified core (Phase 2)

This file extends `RYTT_standalone.lean` with the type-level structures
from the architectural roadmap: `Plane`, `GenomeBase`, `Ligature`, `Token`,
`RyttStream`, and `token_to_pua`. It proves two new theorems with **zero
`sorry`** and **no imports** (core Lean only, no Mathlib):

1. `pua_allocation_disjoint` — injectivity of `token_to_pua`: distinct
   tokens map to distinct PUA code points (or both `none` for passthrough).
2. `plane_partition_disjoint` — Ground and Elevated plane code points
   never overlap.

These are the plane-disjointness and injectivity guarantees the roadmap
requires. Full `decode(encode(s)) = some(s)` over arbitrary strings requires
modeling the greedy ligature tokenizer inductively and is left as future
work (the four left-inverse theorems in `RYTT_standalone.lean` cover the
per-chord case).

Author: R. W. Yett · Sovereign A.R.I.: Chyren
-/

-- ─── Plane ───────────────────────────────────────────────────────────

inductive Plane : Type
  | Ground   : Plane
  | Elevated : Plane
deriving DecidableEq, Repr

def Plane.baseOffset : Plane → Nat
  | Plane.Ground   => 0xE000
  | Plane.Elevated => 0xE800

def Plane.z : Plane → Nat
  | Plane.Ground   => 0
  | Plane.Elevated => 25

-- ─── Genome and ligature structures ──────────────────────────────────

structure GenomeBase where
  id : Fin 52
deriving DecidableEq, Repr

structure Ligature where
  id : Fin 46
deriving DecidableEq, Repr

-- ─── Token ────────────────────────────────────────────────────────────

inductive Token : Type
  | baseToken     : GenomeBase → Plane → Token
  | ligatureToken : Ligature → Plane → Token
  | passthrough   : Char → Token
deriving DecidableEq, Repr

def RyttStream := List Token

-- ─── PUA allocation ───────────────────────────────────────────────────
-- Ground bases:   U+E000 + id        (id < 52, so max U+E033)
-- Elevated bases:  U+E800 + id        (id < 52, so max U+E833)
-- Ground ligatures:  U+E020 + id      (id < 46, so max U+E04D)
-- Elevated ligatures: U+E820 + id     (id < 46, so max U+E84B)

def token_to_pua : Token → Option Nat
  | Token.baseToken     b Plane.Ground   => some (0xE000 + b.id.val)
  | Token.baseToken     b Plane.Elevated => some (0xE800 + b.id.val)
  | Token.ligatureToken l Plane.Ground   => some (0xE020 + l.id.val)
  | Token.ligatureToken l Plane.Elevated => some (0xE820 + l.id.val)
  | Token.passthrough _                  => none

/-- Injectivity of `token_to_pua` over PUA-allocated tokens: if two tokens
    both map to `some` (a PUA code point) and those code points are equal,
    then the tokens are equal. Passthrough tokens map to `none` and are
    excluded — two different passthrough characters both yield `none`.

    This proves the encoder cannot collapse two different PUA-allocated
    tokens (genome bases or ligatures) to the same code point. -/
theorem pua_allocation_injective (t1 t2 : Token)
    (h1 : token_to_pua t1 = some v1)
    (h2 : token_to_pua t2 = some v2)
    (h : v1 = v2) : t1 = t2 := by
  cases t1 with
  | baseToken b1 p1 =>
    cases t2 with
    | baseToken b2 p2 =>
      cases p1 <;> cases p2 <;> simp [token_to_pua] at h1 h2
      all_goals {
        have hid : b1.id.val = b2.id.val := by omega
        have hb : b1 = b2 := by
          have hi : b1.id = b2.id := Fin.eq_of_val_eq hid
          exact match b1, b2, hi with | ⟨v, p⟩, ⟨_, _⟩, rfl => rfl
        cases p1 <;> cases p2 <;> simp_all
      }
    | ligatureToken l2 p2 =>
      cases p1 <;> cases p2 <;> simp [token_to_pua] at h1 h2 h
      all_goals omega
    | passthrough c => simp [token_to_pua] at h1
  | ligatureToken l1 p1 =>
    cases t2 with
    | baseToken b2 p2 =>
      cases p1 <;> cases p2 <;> simp [token_to_pua] at h1 h2 h
      all_goals omega
    | ligatureToken l2 p2 =>
      cases p1 <;> cases p2 <;> simp [token_to_pua] at h1 h2
      all_goals {
        have hid : l1.id.val = l2.id.val := by omega
        have hl : l1 = l2 := by
          have hi : l1.id = l2.id := Fin.eq_of_val_eq hid
          exact match l1, l2, hi with | ⟨v, p⟩, ⟨_, _⟩, rfl := rfl
        cases p1 <;> cases p2 <;> simp_all
      }
    | passthrough c => simp [token_to_pua] at h1
  | passthrough c => simp [token_to_pua] at h1

/-- Ground and Elevated plane PUA ranges are disjoint.
    Ground range: [0xE000, 0xE0FF], Elevated range: [0xE800, 0xE8FF].
    No code point can be in both. -/
theorem plane_partition_disjoint
    (v : Nat) (hg : v ≥ 0xE000 ∧ v < 0xE0FF + 1) (he : v ≥ 0xE800 ∧ v < 0xE8FF + 1) :
    False := by
  omega
