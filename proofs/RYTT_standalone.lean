/-!
# RYTT Sovereign Semiotics — verified core

This file has NO imports. It depends on core Lean only, never Mathlib, which is
why it builds in seconds and is gated in CI on every push.

## What is actually proved here

Four round-trip theorems: `pua_decode (pua_encode c) = c` for each chord
constructor, on bounded domains (`id < 27` for primitives, `id < 100` for
compounds). Zero `sorry`, zero axioms beyond the core.

These are **left inverses on a bounded domain** — not bijections, not
involutions. Earlier docstrings claimed both; neither is proved. Proving
bijectivity additionally requires injectivity of `pua_encode` and surjectivity
onto the valid codepoint range; an involution (`f (f x) = x`) is a different
statement again and is not what these are.

The bounds are load-bearing, not decoration: `0xE000 + 27 = 0xE01B` is the first
compound codepoint, so at `id = 27` a primitive encoding collides with the
compound region. Verified by widening `id < 27` to `id < 28`, which breaks the
proof with `omega` failures at exactly the two primitive theorems.

## Relationship to `RYTT.lean` and `RYTTProofs/`

Those files import Mathlib and **do not compile** — see `../CLAUDE.md`. This file
is independent of them and is the only Lean in the repository whose content is
verified. Do not conflate the two when citing formal results.

Author: R. W. Yett · Arkansas, USA · Sovereign A.R.I.: Chyren
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

/-- Round-trip (left inverse) for Ground primitives, on the domain `id < 27`.

    `pua_decode (pua_encode c) = c`. This is a LEFT INVERSE on a bounded domain,
    not a bijection and not an involution -- both of those were claimed by the
    previous docstring and neither is proved here. The bound is load-bearing:
    `0xE000 + 27 = 0xE01B` is the first compound codepoint, so at `id = 27` the
    encoding collides with the compound region and the theorem is false.
    Verified by widening `id < 27` to `id < 28`, which breaks the proof. -/
theorem rytt_ground_primitive_left_inverse (id : Nat) (h : id < 27) :
    pua_decode (pua_encode (RYTTChord.primitive id SemioticPlane.Ground)) = RYTTChord.primitive id SemioticPlane.Ground := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE000 + id >= 0xE81B) := by omega
  have h2 : ¬(0xE000 + id >= 0xE800) := by omega
  have h3 : ¬(0xE000 + id >= 0xE01B) := by omega
  have h4 : 0xE000 + id >= 0xE000 := by omega
  simp [h1, h2, h3, h4]

/-- Round-trip (left inverse) for Elevated primitives, on the domain `id < 27`.
    Left inverse only -- see the Ground primitive docstring. Bound is load-bearing:
    `0xE800 + 27 = 0xE81B` is the first Elevated compound codepoint. -/
theorem rytt_elevated_primitive_left_inverse (id : Nat) (h : id < 27) :
    pua_decode (pua_encode (RYTTChord.primitive id SemioticPlane.Elevated)) = RYTTChord.primitive id SemioticPlane.Elevated := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE800 + id >= 0xE81B) := by omega
  have h2 : 0xE800 + id >= 0xE800 := by omega
  simp [h1, h2]

/-- Round-trip (left inverse) for Ground compounds, on the domain `id < 100`.
    Left inverse only. Note `len` is carried through decode unchanged rather than
    recovered from the codepoint -- the encoding does not store it. -/
theorem rytt_ground_compound_left_inverse (id : Nat) (len : Nat) (h : id < 100) :
    pua_decode (pua_encode (RYTTChord.compound id SemioticPlane.Ground len)) len = RYTTChord.compound id SemioticPlane.Ground len := by
  dsimp [pua_encode, pua_decode]
  have h1 : ¬(0xE01B + id >= 0xE81B) := by omega
  have h2 : ¬(0xE01B + id >= 0xE800) := by omega
  have h3 : 0xE01B + id >= 0xE01B := by omega
  simp [h1, h2, h3]

/-- Round-trip (left inverse) for Elevated compounds, on the domain `id < 100`.
    Left inverse only; `len` is carried, not recovered. -/
theorem rytt_elevated_compound_left_inverse (id : Nat) (len : Nat) (h : id < 100) :
    pua_decode (pua_encode (RYTTChord.compound id SemioticPlane.Elevated len)) len = RYTTChord.compound id SemioticPlane.Elevated len := by
  dsimp [pua_encode, pua_decode]
  have h1 : 0xE81B + id >= 0xE81B := by omega
  simp [h1]
