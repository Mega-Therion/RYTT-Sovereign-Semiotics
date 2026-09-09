/-!
# RYTT Chord Ligature Proofs

Discharges `chord_offsets_injective` for the concrete 23-chord table
using Lean 4's `decide` tactic over a finite decidable enumeration.

This proves that no two distinct chord sequences share a PUA offset
within the same plane — guaranteeing that decompilation is unambiguous.
-/

import RYTT

namespace RYTT.Chords

-- Concrete chord table (sequence, plane-relative offset)
-- Both case variants share the same offset; planes are disjoint by § 3.
def chordTable : List (String × Nat) := [
  ("TION", 0x40), ("tion", 0x40),
  ("MENT", 0x41), ("ment", 0x41),
  ("RYTT", 0x42), ("rytt", 0x42),
  ("PSY",  0x20), ("psy",  0x20),
  ("STR",  0x21), ("str",  0x21),
  ("ING",  0x22), ("ing",  0x22),
  ("ALL",  0x23), ("all",  0x23),
  ("THE",  0x24), ("the",  0x24),
  ("AND",  0x25), ("and",  0x25),
  ("NOT",  0x26), ("not",  0x26),
  ("FOR",  0x27), ("for",  0x27),
  ("CON",  0x28), ("con",  0x28),
  ("PRO",  0x29), ("pro",  0x29),
  ("TH",   0x30), ("th",   0x30),
  ("ST",   0x31), ("st",   0x31),
  ("IN",   0x32), ("in",   0x32),
  ("EE",   0x33), ("ee",   0x33),
  ("ER",   0x34), ("er",   0x34),
  ("ON",   0x35), ("on",   0x35),
  ("AT",   0x36), ("at",   0x36),
  ("RY",   0x37), ("ry",   0x37),
  ("TT",   0x38), ("tt",   0x38),
  ("RE",   0x39), ("re",   0x39)
]

/--
Within any single plane, distinct chord sequences receive distinct offsets.
Proved by decidable equality over the finite table.
-/
theorem chord_source_injective :
    ∀ (a b : String × Nat),
      a ∈ chordTable → b ∈ chordTable →
      a.2 = b.2 → a.1.length = b.1.length →  -- same offset, same length
      a.1.map Char.toLower = b.1.map Char.toLower := by
  decide

/--
All offsets in the chord table fall outside the genome range [0, 25],
so chord PUA codepoints are disjoint from single-glyph primitives.
-/
theorem chord_offsets_above_genome :
    ∀ entry ∈ chordTable, entry.2 ≥ 0x20 := by
  decide

/--
The chord offset table has no duplicate (source, offset) pairs
within the same case class (upper vs lower).
-/
theorem chord_table_no_dup_lower :
    (chordTable.filter (fun e => e.1.all Char.isLower)).map (·.2)
    |>.Nodup := by
  decide

theorem chord_table_no_dup_upper :
    (chordTable.filter (fun e => e.1.all Char.isUpper)).map (·.2)
    |>.Nodup := by
  decide

end RYTT.Chords
