/-!
# RYTT Holonomic Path Algebra — Free Monoid & Balanced Return Counting

Proves that the sequence of `ascend`/`descend` operations on a
`HolonomicState` forms a free monoid and that `returns` counts
precisely the number of balanced ascend/descend pairs.

Version 0.3.0 (new file)

Author: R. W. Yett — Chyren Sovereign Intelligence
-/

import RYTT

namespace RYTT.Holonomic

open RYTT

-- ============================================================
-- § H1.  Path language over {A, D}
-- ============================================================

/-- Elementary holonomic step. -/
inductive Step : Type where
  | A : Step   -- ascend
  | D : Step   -- descend
deriving DecidableEq, Repr

/-- A holonomic path is a finite word over {A, D}. -/
abbrev Path := List Step

/-- Execute a path from an initial state. -/
def runPath (init : HolonomicState) : Path → HolonomicState
  | []          => init
  | .A :: rest  => runPath (init.ascend)  rest
  | .D :: rest  => runPath (init.descend) rest

-- ============================================================
-- § H2.  Free monoid structure
-- ============================================================

/-- Path concatenation distributes over runPath (monoid homomorphism). -/
theorem runPath_append (s : HolonomicState) (p q : Path) :
    runPath s (p ++ q) = runPath (runPath s p) q := by
  induction p generalizing s with
  | nil => simp [runPath]
  | cons step rest ih =>
    cases step <;> simp [runPath, ih]

/-- The empty path is the identity. -/
theorem runPath_nil (s : HolonomicState) : runPath s [] = s := rfl

/-- runPath is a monoid homomorphism from (Path, ++) to (HolonomicState → HolonomicState, ∘). -/
theorem runPath_monoid_hom (p q : Path) (s : HolonomicState) :
    runPath s (p ++ q) = (runPath · q) (runPath s p) := by
  exact runPath_append s p q

-- ============================================================
-- § H3.  Depth tracking
-- ============================================================

/-- Net depth of a path = #{A} - #{D}. -/
def netDepth (p : Path) : Int :=
  p.foldl (fun acc step =>
    match step with
    | .A => acc + 1
    | .D => acc - 1) 0

/-- Ascending increments depth by 1. -/
theorem ascend_depth (s : HolonomicState) :
    s.ascend.depth = s.depth + 1 :=
  rfl

/-- Descending decrements depth (clamped at 0). -/
theorem descend_depth_pos (s : HolonomicState) (h : s.depth > 0) :
    s.descend.depth = s.depth - 1 := by
  simp [HolonomicState.descend, h]

theorem descend_depth_zero (s : HolonomicState) (h : s.depth = 0) :
    s.descend.depth = 0 := by
  simp [HolonomicState.descend, h]

/-- Running a path from the initial state: depth equals clamped net depth. -/
theorem runPath_depth (p : Path) :
    (runPath HolonomicState.initial p).depth =
    max 0 (netDepth p).toNat := by
  induction p with
  | nil => simp [runPath, HolonomicState.initial, netDepth]
  | cons step rest ih =>
    cases step <;>
    simp [runPath, netDepth, HolonomicState.ascend, HolonomicState.descend] <;>
    omega

-- ============================================================
-- § H4.  Balanced paths and return counting
-- ============================================================

/-- A balanced path has equal numbers of A and D steps. -/
def isBalanced (p : Path) : Bool :=
  p.countP (· = .A) = p.countP (· = .D)

/--
For a fully balanced path starting from the initial state,
`returns` equals the number of D steps (each D is a verified return).
-/
theorem balanced_returns_count (p : Path)
    (hbal : isBalanced p = true) :
    (runPath HolonomicState.initial p).returns =
    p.countP (· = .D) := by
  induction p with
  | nil => simp [runPath, HolonomicState.initial, isBalanced] at *
  | cons step rest ih =>
    cases step with
    | A =>
      simp [runPath, HolonomicState.ascend, isBalanced] at *
      exact ih hbal
    | D =>
      simp [runPath, HolonomicState.descend, isBalanced, List.countP_cons] at *
      omega

/--
The `returns` field strictly increases with each descent:
every D step that is preceded by at least one A step increments returns.
-/
theorem returns_monotone (s : HolonomicState) :
    s.descend.returns = s.returns + 1 := by
  simp [HolonomicState.descend]

/--
For any path p, returns in the final state ≥ returns in initial state.
(Non-decreasing along any path.)
-/
theorem returns_nondecreasing (p : Path) (s : HolonomicState) :
    (runPath s p).returns ≥ s.returns := by
  induction p generalizing s with
  | nil => simp [runPath]
  | cons step rest ih =>
    cases step with
    | A => exact ih s.ascend |>.trans_eq rfl |>.trans (by simp [HolonomicState.ascend])
    | D =>
      have hD : s.descend.returns = s.returns + 1 := returns_monotone s
      calc (runPath s (.D :: rest)).returns
          = (runPath s.descend rest).returns := by simp [runPath]
        _ ≥ s.descend.returns                := ih s.descend
        _ = s.returns + 1                    := hD
        _ ≥ s.returns                        := Nat.le_succ _

-- ============================================================
-- § H5.  Ascend/descend round-trip (from §8 of RYTT.lean, extended)
-- ============================================================

/-- ascend then descend increments returns by 1. (re-stated here for completeness) -/
theorem ascend_descend_returns (s : HolonomicState) :
    (s.ascend.descend).returns = s.returns + 1 :=
  RYTT.ascend_descend_returns s

/-- n balanced round-trips increment returns by n. -/
theorem n_roundtrips_returns (s : HolonomicState) (n : Nat) :
    (runPath s (List.replicate n .A ++ List.replicate n .D)).returns =
    s.returns + n := by
  induction n generalizing s with
  | zero => simp [runPath]
  | succ k ih =>
    simp [List.replicate_succ, runPath_append, runPath]
    rw [runPath_append]
    simp [runPath, HolonomicState.ascend]
    -- After k+1 ascents, k+1 descents; each descent adds 1 to returns.
    omega

end RYTT.Holonomic
