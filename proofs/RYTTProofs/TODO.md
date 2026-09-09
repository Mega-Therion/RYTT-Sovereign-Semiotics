# Proof TODO — tracked work items

## Open (v0.2.0 → v0.3.0)

- [ ] **Full compiler induction**: wire Python `compiler.py` lookup tables
  as Lean `def`s and prove `D(C(S)) ≡ S` by structural induction over the
  greedy tokeniser loop. Requires formalising the greedy longest-match
  algorithm as a Lean `def` and proving termination.

- [ ] **Discharge `chord_offsets_injective` axiom**: the `decide` tactic
  proofs in `Chords.lean` cover injectivity structurally; the axiom in
  `RYTT.lean` should be replaced with a direct corollary of those proofs.

- [ ] **VSA quasi-orthogonality**: prove that for D=10240 randomly drawn
  binary hypervectors, Hamming distance concentrates around D/2 with
  deviation bounded by √D — the foundation for multi-token retrieval
  correctness.  Requires Mathlib probability / measure theory.

- [ ] **4Leibniz chain rule**: extend `product_rule_ground` to all four
  δ operators and prove the full chain rule:
  `δ_op(A ++ B, i) = δ_op(A, i) ++ δ_op(B, i - |A|)` for i ≥ |A|.

- [ ] **Holonomic path algebra**: prove that the sequence of `ascend`/`descend`
  operations forms a free monoid and that `returns` counts balanced pairs.

- [ ] **Parity block homomorphism**: prove that the parity map
  `Sequence → ℤ/24ℤ` is a ring homomorphism with respect to concatenation.
