-- RYTT Sovereign Semiotics — Lean 4 lake build file
import Lake
open Lake DSL

package rytt where
  version := v!"0.2.0"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "5eec30bc56ed5a23be2e27c544a949ba0bceddeb"

lean_lib RYTT where
  roots := #[`RYTT]

lean_lib RYTTProofs where
  roots := #[`RYTTProofs]

@[default_target]
lean_exe rytt_check where
  root := `Main
