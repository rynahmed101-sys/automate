- [x] Null space, row space, column space
- [x] Basis, span, linear independence
- [x] Change of basis and coordinate representations
- [x] Linear transformations and matrix representations
- [x] Symmetric / Hermitian matrices
- [x] Norms, inner products, orthogonality
- [x] Projections and Gram-Schmidt
- [x] Positive-definite matrices
- [x] Quadratic forms
- [x] Singular-value decomposition
- [x] Moore-Penrose pseudoinverse and least-squares solutions
- [x] Complex scalar/vector/matrix semantics needed by later quantum and spectral reasoning

**Depth rule:** vector/matrix operations should be dimension-generic where represented; subspace and basis operations must correctly handle rectangular, rank-deficient, zero-dimensional, symbolic, and degenerate cases.

## 1B. Calculus

- [ ] Limits and continuity
- [ ] Derivatives and higher-order derivatives
- [ ] Chain/product/quotient and implicit differentiation
- [ ] Higher-order symbolic differentiation without arbitrary order ceilings
- [ ] Definite and indefinite integration
- [ ] Repeated/nested integration where represented
- [ ] Substitution, integration by parts, partial fractions, trigonometric and other general integration techniques where tractable
- [x] Fundamental theorem of calculus
- [x] Improper integrals and convergence-aware handling
- [ ] Taylor / Maclaurin series and higher-order expansions
- [ ] Partial derivatives and total differentials
- [ ] Higher-order partial derivatives
- [ ] Jacobians and Hessians
- [ ] Multivariable chain rule
- [ ] Stationary points and constrained optimization
- [ ] Domain/singularity/assumption-aware calculus

**Depth rule:** “derivative” means a general differentiation capability, not a permanently hard-coded first-derivative feature. The same principle applies to integrals, series order, and multivariable operations.

**Control-plane frontier:** the next claimable Stage 1B capability is **Taylor / Maclaurin series and higher-order expansions** (GitHub issue #141). Improper integrals are merged into authoritative main; their exact-head/security verification record is being reconciled on the current main line. Stage 1C ODE implementation is preserved as later work and must not leapfrog the remaining 1B ladder.

## 1C. General ODEs

- [ ] Separable first-order equations
- [ ] Linear first-order equations
- [ ] Bernoulli / exact equations
- [ ] Higher-order constant-coefficient families
- [ ] General linear ODE representations where tractable
- [ ] Coupled ODE systems
- [ ] Initial-value and boundary-value problems
- [ ] Phase-space representations
- [ ] Verification of proposed ODE solutions
- [ ] Domain and initial/boundary-condition validation

**Depth rule:** second-order examples are stepping stones, not the permanent ceiling.

### Stage 1 exit condition

Stage 1 is complete only when its mathematical machinery is sufficiently general to serve later physics without repeatedly returning for missing elementary operators.

**Current status:** [~] Active. Stage 1A and the implemented Stage 1B calculus stack are merged into main. Improper integrals (Issue #115) are now merged, while the latest exact-head run exposed stale frontier assertions that are being corrected by the current reconciliation PR. The next claimable capability is Series expansions (Issue #141). Stage 1C ODE work remains preserved out of order.

---
