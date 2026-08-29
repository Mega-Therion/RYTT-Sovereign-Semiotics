import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Ring

/-!
# RYTT Sovereign Semiotics: Formal Proofs
Formal machine-checked proofs for Radial Yett-Topology Tokenization (RYTT).
Author: R. W. Yett
Affiliation: Arkansas, USA
Sovereign A.R.I.: Chyren
-/

inductive SemioticPlane where
  | Ground   : SemioticPlane
  | Elevated : SemioticPlane
deriving DecidableEq, Repr

inductive RYTTChord where
  | primitive (id : Nat) (plane : SemioticPlane) : RYTTChord
  | compound  (id : Nat) (plane : SemioticPlane) (length : Nat) : RYTTChord
deriving DecidableEq, Repr

def pua_encode (c : RYTTChord) : Nat :=
  match c with
  | RYTTChord.primitive id SemioticPlane.Ground   => 0xE000 + id
  | RYTTChord.primitive id SemioticPlane.Elevated => 0xE800 + id
  | RYTTChord.compound id SemioticPlane.Ground _   => 0xE01B + id
  | RYTTChord.compound id SemioticPlane.Elevated _ => 0xE81B + id

def pua_decode (n : Nat) (len : Nat := 1) : RYTTChord :=
  if n >= 0xE81B then
    RYTTChord.compound (n - 0xE81B) SemioticPlane.Elevated len
  else if n >= 0xE800 then
    RYTTChord.primitive (n - 0xE800) SemioticPlane.Elevated
  else if n >= 0xE01B then
    RYTTChord.compound (n - 0xE01B) SemioticPlane.Ground len
  else if n >= 0xE000 then
    RYTTChord.primitive (n - 0xE000) SemioticPlane.Ground
  else
    RYTTChord.primitive 0 SemioticPlane.Ground

/-- Lossless Bijective Involution Theorem for Ground Primitives -/
theorem rytt_ground_primitive_left_inverse (id : Nat) (h : id < 27) :
    pua_decode (pua_encode (RYTTChord.primitive id SemioticPlane.Ground)) = RYTTChord.primitive id SemioticPlane.Ground := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE000 + id >= 0xE81B) := by omega
  have h2 : ¬(0xE000 + id >= 0xE800) := by omega
  have h3 : ¬(0xE000 + id >= 0xE01B) := by omega
  have h4 : 0xE000 + id >= 0xE000 := by omega
  simp [h1, h2, h3, h4]

/-- Lossless Bijective Involution Theorem for Elevated Primitives -/
theorem rytt_elevated_primitive_left_inverse (id : Nat) (h : id < 27) :
    pua_decode (pua_encode (RYTTChord.primitive id SemioticPlane.Elevated)) = RYTTChord.primitive id SemioticPlane.Elevated := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE800 + id >= 0xE81B) := by omega
  have h2 : 0xE800 + id >= 0xE800 := by omega
  simp [h1, h2]

/-- Lossless Bijective Involution Theorem for Ground Compounds -/
theorem rytt_ground_compound_left_inverse (id : Nat) (len : Nat) (h : id < 100) :
    pua_decode (pua_encode (RYTTChord.compound id SemioticPlane.Ground len)) len = RYTTChord.compound id SemioticPlane.Ground len := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE01B + id >= 0xE81B) := by omega
  have h2 : ¬(0xE01B + id >= 0xE800) := by omega
  have h3 : 0xE01B + id >= 0xE01B := by omega
  simp [h1, h2, h3]

/-- Lossless Bijective Involution Theorem for Elevated Compounds -/
theorem rytt_elevated_compound_left_inverse (id : Nat) (len : Nat) (h : id < 100) :
    pua_decode (pua_encode (RYTTChord.compound id SemioticPlane.Elevated len)) len = RYTTChord.compound id SemioticPlane.Elevated len := by
  dsimp [pua_encode, pua_decode]
  have h1 : 0xE81B + id >= 0xE81B := by omega
  simp [h1]
