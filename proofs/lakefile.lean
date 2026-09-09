-- RYTT Sovereign Semiotics — Lean 4 lake build file
import Lake
open Lake DSL

package rytt where
  name := `rytt
  version := "0.2.0"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4"

lean_lib RYTT where
  roots := #[`RYTT]

lean_lib RYTTProofs where
  roots := #[`RYTTProofs]

@[default_target]
lean_exe rytt_check where
  root := `Main
