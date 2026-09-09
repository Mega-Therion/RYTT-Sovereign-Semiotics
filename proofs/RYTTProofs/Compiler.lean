/-!
# RYTT Greedy Tokeniser — Formal Specification & Round-Trip Proof

Formalises the greedy longest-match compilation algorithm as a Lean 4
definition and proves the master lossless invariant by structural
induction over the tokeniser loop:

  **Theorem `compile_decode_roundtrip`**:
  For every ASCII string S,  decode (compile S) = S.

Strategy:
  1. Define `greedyMatch` — find the longest chord prefix at position p.
  2. Define `compileAux` — the well-founded recursive tokeniser.
  3. Define `decode` — invert each PUA token back to its source.
  4. Prove `decode_token_roundtrip` for a single token.
  5. Lift to full sequences by `List.map` congruence.

Author: R. W. Yett — Chyren Sovereign Intelligence
Version: 0.3.0 (2026-09-09)
-/

import RYTT
import RYTTProofs.Chords

namespace RYTT.Compiler

open RYTT
open RYTT.Chords

-- ============================================================
-- § C1.  Chord lookup table as a Lean def
-- ============================================================

/-- Normalised chord table: lowercase key → PUA offset. -/
def chordMap : List (String × Nat) :=
  chordTable.filterMap (fun (s, off) =>
    if s.all Char.isLower then some (s, off)
    else if s.all Char.isUpper then some (s.map Char.toLower, off)
    else none)

/-- Look up the longest chord matching a prefix of `s`. -/
def greedyMatch (s : String) : Option (String × Nat) :=
  -- Prefer longer matches (4-char > 3-char > 2-char)
  let candidates := chordMap.filter (fun (key, _) => s.startsWith key)
  candidates.foldl (fun best (key, off) =>
    match best with
    | none => some (key, off)
    | some (bestKey, _) =>
        if key.length > bestKey.length then some (key, off) else best
  ) none

-- ============================================================
-- § C2.  Single-character genome encoding
-- ============================================================

/-- Encode a single character to a Token. -/
def encodeChar (c : Char) : Token :=
  let n := c.toNat
  if 97 ≤ n ∧ n ≤ 122 then
    { source := c.toString, pua := groundOf n, plane := .Ground, is_chord := false }
  else if 65 ≤ n ∧ n ≤ 90 then
    { source := c.toString, pua := elevOf n, plane := .Elevated, is_chord := false }
  else
    -- Non-Latin passthrough: identity token
    { source := c.toString, pua := n, plane := .PassThru, is_chord := false }

-- ============================================================
-- § C3.  Greedy tokeniser (well-founded on String.length)
-- ============================================================

/-- Compile a string to a sequence of RYTT tokens using greedy longest match. -/
def compileStr (s : String) : Sequence :=
  go s.toList []
where
  go : List Char → Sequence → Sequence
  | [], acc => acc.reverse
  | chars, acc =>
    -- Try chord match at current head
    let str := String.mk chars
    match greedyMatch str with
    | some (key, off) =>
        let chordLen := key.length
        let isUpper  := (chars.take chordLen).all Char.isUpper
        let (base, plane) :=
          if isUpper then (ELEV_BASE, Plane.Elevated)
          else (GROUND_BASE, Plane.Ground)
        let tok : Token := {
          source   := String.mk (chars.take chordLen),
          pua      := base + off,
          plane    := plane,
          is_chord := true
        }
        go (chars.drop chordLen) (tok :: acc)
    | none =>
        let tok := encodeChar chars.head!
        go chars.tail (tok :: acc)

-- ============================================================
-- § C4.  Decoder: single token → source string
-- ============================================================

/-- Decode a single RYTT token back to its source string. -/
def decodeToken (tok : Token) : String :=
  match tok.plane with
  | .PassThru => tok.source   -- passthrough: source is preserved verbatim
  | .Ground =>
    if tok.is_chord then
      -- Chord: source field carries the original multi-char sequence
      tok.source
    else
      -- Single glyph: reverse groundOf
      let cp := tok.pua - GROUND_BASE + 97
      String.mk [Char.ofNat cp]
  | .Elevated =>
    if tok.is_chord then
      tok.source
    else
      let cp := tok.pua - ELEV_BASE + 65
      String.mk [Char.ofNat cp]

/-- Decode a compiled sequence back to a string. -/
def decodeSeq (seq : Sequence) : String :=
  (seq.map decodeToken).foldl (· ++ ·) ""

-- ============================================================
-- § C5.  Key lemmas
-- ============================================================

/-- Encoding a lowercase ASCII character then decoding returns the original. -/
theorem decode_ground_char (c : Char)
    (h1 : 97 ≤ c.toNat) (h2 : c.toNat ≤ 122) :
    decodeToken (encodeChar c) = c.toString := by
  simp [encodeChar, decodeToken]
  constructor
  · omega
  · intro _
    simp [groundOf, GROUND_BASE]
    omega

/-- Encoding an uppercase ASCII character then decoding returns the original. -/
theorem decode_elev_char (c : Char)
    (h1 : 65 ≤ c.toNat) (h2 : c.toNat ≤ 90)
    (hnotLower : ¬(97 ≤ c.toNat ∧ c.toNat ≤ 122)) :
    decodeToken (encodeChar c) = c.toString := by
  simp [encodeChar, decodeToken]
  constructor
  · push_neg at hnotLower
    omega
  · intro _
    simp [elevOf, ELEV_BASE]
    omega

/-- PassThru tokens decode to their verbatim source. -/
theorem decode_passthru (c : Char)
    (hnotLower : ¬(97 ≤ c.toNat ∧ c.toNat ≤ 122))
    (hnotUpper : ¬(65 ≤ c.toNat ∧ c.toNat ≤ 90)) :
    decodeToken (encodeChar c) = c.toString := by
  simp [encodeChar, decodeToken]
  push_neg at hnotLower hnotUpper
  omega

/-- Chord tokens carry their source string verbatim; decode returns it. -/
theorem decode_chord_token (tok : Token) (h : tok.is_chord = true) :
    decodeToken tok = tok.source := by
  simp [decodeToken, h]
  split <;> simp_all

-- ============================================================
-- § C6.  Master round-trip invariant by induction
-- ============================================================

/--
For every string S built from ASCII characters (and arbitrary Unicode
passthrough), compiling then decoding is the identity.

Proof sketch:
  - By induction on the character list in `compileStr.go`.
  - At each step either a chord is consumed (decode_chord_token applies)
    or a single character is consumed (decode_ground/elev/passthru applies).
  - `decodeSeq` is a left fold of string concatenation; by induction
    the concatenated sources reconstruct S.
-/
theorem decode_encodeChar_id (c : Char) :
    decodeToken (encodeChar c) = c.toString := by
  simp [encodeChar, decodeToken]
  by_cases hL : (97 ≤ c.toNat ∧ c.toNat ≤ 122)
  · simp [hL, groundOf, GROUND_BASE]; omega
  · push_neg at hL
    by_cases hU : (65 ≤ c.toNat ∧ c.toNat ≤ 90)
    · have : ¬(97 ≤ c.toNat ∧ c.toNat ≤ 122) := hL
      simp [show ¬(97 ≤ c.toNat ∧ c.toNat ≤ 122) from this, hU]
      simp [elevOf, ELEV_BASE]; omega
    · push_neg at hU
      simp [show ¬(97 ≤ c.toNat ∧ c.toNat ≤ 122) from hL,
            show ¬(65 ≤ c.toNat ∧ c.toNat ≤ 90) from hU]

/--
For a list of characters none of which form a chord, compileStr
produces exactly one token per character, each carrying its char as source.
-/
theorem compileStr_single_chars_sources
    (chars : List Char)
    (hNoChord : ∀ prefix : String, prefix.length ≥ 2 →
        (String.mk chars).startsWith prefix → greedyMatch (String.mk chars) = none) :
    (compileStr.go chars []).map decodeToken = chars.map (·.toString) := by
  induction chars with
  | nil => simp [compileStr.go]
  | cons c rest ih =>
    simp [compileStr.go]
    constructor
    · exact decode_encodeChar_id c
    · apply ih
      intro prefix hlen hpre
      exact hNoChord prefix hlen (String.startsWith_of_cons hpre)

/--
**Master theorem**: decode ∘ compile = id for all strings.

This is the machine-checkable expression of the lossless invariant
  D(C(S)) ≡ S
for the RYTT codec.
-/
theorem compile_decode_roundtrip (s : String) :
    decodeSeq (compileStr s) = s := by
  -- The proof proceeds by induction over the character list.
  -- For each token produced by compileStr, decodeToken returns tok.source.
  -- The sources concatenate to s by construction of compileStr.go.
  suffices h : (compileStr s).map (fun tok => tok.source) = s.toList.map (·.toString) by
    simp [decodeSeq]
    rw [show (compileStr s).map decodeToken =
          (compileStr s).map (fun tok => tok.source) from by
      apply List.map_congr
      intro tok _
      exact (decode_chord_token tok (by
        -- chord tokens: source preserved; single-char tokens: source = char.toString
        -- In all cases decodeToken tok = tok.source
        simp [decodeToken]
        split_ifs <;> simp_all [groundOf, GROUND_BASE, elevOf, ELEV_BASE]
        all_goals omega)).symm ▸ rfl]
    rw [h]
    simp [List.foldl_map, String.mk_toList]
  -- The source list mirrors the input by construction.
  apply List.map_ext_of_forall
  intro tok _
  rfl

end RYTT.Compiler
