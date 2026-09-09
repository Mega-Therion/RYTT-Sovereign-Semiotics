import Lake
open Lake DSL

package "RYTTProofs" where
  name := "RYTTProofs"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @ "v4.14.0"

lean_lib RYTTProofs where
  roots := #[
    `RYTT,
    `RYTTProofs.Chords,
    `RYTTProofs.Compiler,
    `RYTTProofs.VSA,
    `RYTTProofs.Leibniz,
    `RYTTProofs.Holonomic,
    `RYTTProofs.Parity
  ]
