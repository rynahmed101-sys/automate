# Linear Algebra Complex Semantics

Automate's later spectral and quantum reasoning requires explicit complex linear-algebra semantics rather than treating complex matrices as an incidental extension of real arithmetic.

## Current capability

Stage 1A exposes two reusable operations:

- `matrix_conjugate_transpose`: verifies the adjoint/conjugate-transpose of an explicit real or complex matrix.
- `matrix_unitary`: verifies the square-matrix condition A^H A = I. Symbolic cases that cannot establish the condition fail closed as UNVERIFIED.

The canonical semantics are implemented in Automate's linear-algebra backend using SymPy expressions. NumPy is used only as independent numerical evidence where the inputs are numeric.

## Boundaries

Real matrices use the same operation correctly because conjugation leaves real entries unchanged. Unitarity is distinct from ordinary transpose-based orthogonality: complex matrices require conjugate-transpose semantics.

Malformed dimensions, non-square unitary candidates, incorrect claims, and unresolved symbolic conditions are not guessed through. These cases are rejected or classified as UNVERIFIED according to the available evidence.

This packet now includes the central rule-registry and agent-contract exposure, but it remains an implementation/review milestone until merged-main Exact-head and Security verification complete.
