# Stage 3A — Scalar-Field Variational Foundation

Automate already contained a variational field-theory subsystem. This work hardens that subsystem rather than creating a parallel implementation.

## Implemented

- Explicit scalar field and independent-coordinate representation through FieldTheoryAction.
- Symbolic Lagrangian-density parsing.
- General first-derivative Euler-Lagrange construction for one or multiple scalar fields:
  dL/dphi - sum_mu d_mu(dL/d(d_mu phi)) = 0.
- Symbolic candidate-equation verification using expression equivalence rather than string matching.
- Multiple interacting scalar fields.
- Symbolic parameters and arbitrary supported coordinate lists.
- Explicit boundary-variation assumption requirement for verification.
- Rejection of duplicate/empty field or coordinate specifications.
- Fail-closed rejection of higher-order field derivatives, which are outside this foundation.
- Rejection of candidate equations for undeclared fields and malformed multi-equality expressions.

## Evidence boundary

A derived Euler-Lagrange expression can be constructed without declaring boundary conditions, but candidate verification is UNVERIFIED unless the explicit assumption identifier vanishing_boundary_variations is declared. This prevents the stationary-action boundary step from being silently assumed.

Equivalent equations are accepted when symbolic simplification proves equivalence. A whole-equation sign reversal is also equivalent because the equation is asserted to equal zero.

## Intentionally incomplete

- Higher-order Euler-Lagrange equations.
- Tensor-valued field variation and general metric variation.
- Gauge-field variation and gauge fixing.
- Noether-current construction.
- Stress-energy tensor derivation.
- Boundary terms and non-vanishing boundary variations.
- Automated spacetime metric/connection variation.
