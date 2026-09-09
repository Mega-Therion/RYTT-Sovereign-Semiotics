/-!
# RYTT Lean 4 — Main check entry point

Runs `#check` on all master theorems to confirm the proof stack
compiles without errors.  Execute with:
  lake exe rytt_check
-/

import RYTTProofs.Integration

open RYTT RYTT.Integration RYTT.VSA RYTT.Leibniz

-- Verify all four layers are in scope
#check @layer1_ground_rt
#check @layer1_elev_rt
#check @layer3_vsa_lossless
#check @layer4_leibniz_identity
#check @layer_holonomic_return
#check @layer_parity_24
#check @rytt_formal_stack

#eval "RYTT Lean 4 formal stack: all theorems compiled."
