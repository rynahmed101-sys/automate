# Automate Project Phase Ledger

This is the human-readable project scoreboard for the Maths & Physics capability program.

The ledger is maintained by the project lead/engineering agent. It records project state in plain English.

## Status key

- [ ] Not started
- [~] In progress
- [!] Verification pending
- [x] Completed and verified

A merged feature is **not** marked [x] until its acceptance evidence and exact-head CI verification are complete.

## Current position

**Current main:** `36aeddcfe99e04f122db8721de039b7933e7e74a`

**Current work:** Linear Algebra Phase 1A eigenproblem extension has been merged.

**Current verification gate:** Exact `main` CI + Security Audit are queued for the merged SHA, so this batch is **[!] Verification pending**, not complete.

**Next capability after this gate:** Linear Algebra inner-product / orthogonality extension, then Vector Calculus.

---

# Phase 1 — Mathematical Foundations

## Linear Algebra
- [x] Core vectors and vector operations
- [x] Matrices, shapes, multiplication, transpose
- [x] Determinant, trace, inverse, rank
- [x] Gaussian elimination, RREF, unique Ax=b solving
- [!] Characteristic polynomial
- [!] Eigenvalues with multiplicity
- [!] Eigenvector verification
- [!] Diagonalization
- [ ] Null space, row space, column space
- [ ] Basis, span, linear independence
- [ ] Change of basis
- [ ] Symmetric / Hermitian matrices
- [ ] Norms, inner products, orthogonality
- [ ] Projections and Gram-Schmidt
- [ ] Positive-definite matrices
- [ ] Quadratic forms

## Core Calculus
- [ ] Limits and continuity
- [ ] Definite and indefinite integration
- [ ] Integration techniques
- [ ] Taylor / Maclaurin series
- [ ] Partial derivatives and total differentials
- [ ] Jacobians and Hessians
- [ ] Multivariable chain rule
- [ ] Stationary points and constrained optimization

## General ODEs
- [ ] Separable first-order equations
- [ ] Linear first-order equations
- [ ] Bernoulli / exact equations
- [ ] Second-order constant-coefficient families
- [ ] Coupled ODE systems
- [ ] Initial-value and boundary-value problems
- [ ] Phase-space representations

**Phase 1 status:** [~] Foundations are being expanded capability-first.

---

# Phase 2 — Vector Calculus & Electromagnetism

## Vector Calculus
- [ ] Scalar and vector fields
- [ ] Gradient
- [ ] Directional derivative
- [ ] Divergence
- [ ] Curl
- [ ] Laplacian
- [ ] Line / surface / volume integrals
- [ ] Conservative fields and potentials
- [ ] Flux
- [ ] Green's theorem
- [ ] Divergence theorem
- [ ] Stokes' theorem

## Electrostatics
- [ ] Coulomb law
- [ ] Electric field and potential
- [ ] Charge distributions
- [ ] Gauss law
- [ ] Conductors and capacitors
- [ ] Dipoles and electrostatic energy
- [ ] Boundary conditions

## Magnetostatics
- [ ] Biot-Savart law
- [ ] Ampere law
- [ ] Magnetic fields
- [ ] Vector potential
- [ ] Magnetic dipoles
- [ ] Gauge conditions where represented

## Maxwell
- [ ] Differential Maxwell equations
- [ ] Integral Maxwell equations
- [ ] Differential ↔ integral form checks
- [ ] Charge conservation
- [ ] Electromagnetic potentials
- [ ] Lorentz force
- [ ] Poynting vector
- [ ] Electromagnetic wave equation

**Phase 2 status:** [ ] Not started.

---

# Phase 3 — Advanced Calculus, PDEs, Waves & Expanded Mechanics

## PDEs
- [ ] Heat equation
- [ ] Wave equation
- [ ] Laplace / Poisson equations
- [ ] Separation of variables
- [ ] Initial and boundary conditions
- [ ] Fourier-series solutions
- [ ] Green-function methods where tractable

## Fourier / Laplace
- [ ] Fourier series
- [ ] Fourier transforms
- [ ] Inverse transforms
- [ ] Convolution
- [ ] Laplace transforms
- [ ] Inverse Laplace transforms

## Classical Mechanics Expansion
- [ ] Constraints and Lagrange multipliers
- [ ] Hamilton equations
- [ ] Poisson brackets
- [ ] Canonical transformations
- [ ] Central-force / Kepler problems
- [ ] Coupled oscillators and normal modes
- [ ] Rigid-body motion
- [ ] Rotating frames

## Waves and Optics
- [ ] Harmonic waves
- [ ] Superposition and interference
- [ ] Standing waves
- [ ] Dispersion
- [ ] Reflection / refraction
- [ ] Polarization
- [ ] Basic diffraction

**Phase 3 status:** [ ] Not started.

---

# Phase 4 — Relativity, Geometry & Differential Forms

## Tensor Algebra
- [ ] Tensor index contraction
- [ ] Raise tensor index
- [ ] Lower tensor index
- [ ] Arbitrary-rank tensor operations
- [ ] Symmetrization / antisymmetrization
- [ ] Kronecker delta
- [ ] Levi-Civita symbol/tensor
- [ ] Covariant derivatives
- [ ] Metric compatibility
- [ ] Coordinate transformations
- [ ] Lie derivatives

## Differential Forms
- [ ] One-forms and p-forms
- [ ] Wedge product
- [ ] Exterior derivative
- [ ] Pullback
- [ ] Hodge dual
- [ ] Exterior-calculus identities

## Special Relativity
- [ ] Lorentz transformations
- [ ] Minkowski metric
- [ ] Proper time
- [ ] Four-vectors
- [ ] Four-momentum
- [ ] Four-current
- [ ] Electromagnetic field tensor

## General Relativity
- [ ] Covariant-derivative expansion
- [ ] Curvature invariants
- [ ] Stress-energy tensor
- [ ] Einstein field equations
- [ ] Conservation laws
- [ ] Killing vectors
- [ ] Geodesic deviation
- [ ] Schwarzschild spacetime
- [ ] Weak-field / Newtonian limit
- [ ] FLRW and Friedmann equations

**Phase 4 status:** [~] Existing geometry foundation exists; tensor capabilities still need expansion.

---

# Phase 5 — Thermodynamics & Statistical Physics

## Thermodynamics
- [ ] State variables and equations of state
- [ ] First law
- [ ] Second law
- [ ] Entropy
- [ ] Enthalpy
- [ ] Helmholtz / Gibbs free energies
- [ ] Maxwell relations
- [ ] Carnot cycle
- [ ] Phase equilibrium

## Statistical Mechanics
- [ ] Microstates / macrostates
- [ ] Multiplicity
- [ ] Boltzmann distribution
- [ ] Partition functions
- [ ] Canonical ensemble
- [ ] Grand canonical ensemble
- [ ] Expectation values and fluctuations
- [ ] Equipartition
- [ ] Simple spin systems

**Phase 5 status:** [ ] Not started.

---

# Phase 6 — Numerical Mathematics & Scientific Computing

- [ ] Numerical root finding
- [ ] Nonlinear equation systems
- [ ] Numerical differentiation
- [ ] Numerical integration / quadrature
- [ ] Interpolation
- [ ] Optimization
- [ ] Numerical linear algebra
- [ ] Numerical eigenproblems
- [ ] FFT
- [ ] Monte Carlo methods
- [ ] Parameter sweeps
- [ ] Sensitivity analysis
- [ ] Uncertainty propagation
- [ ] Numerical PDE methods
- [ ] Conditioning / residual evidence
- [ ] Convergence evidence

**Phase 6 status:** [~] Numerical ODE capability already exists; broader numerical mathematics remains.

---

# Phase 7 — Approximation, Perturbation & Conservation

## Approximation
- [ ] Taylor expansion as a controlled approximation
- [ ] Small-parameter expansion
- [ ] Linearization
- [ ] Asymptotic notation
- [ ] Perturbation series
- [ ] Weak-field approximation
- [ ] Small-angle approximation
- [ ] Nonrelativistic limits
- [ ] Semiclassical limits

## Conservation
- [ ] Energy
- [ ] Linear momentum
- [ ] Angular momentum
- [ ] Charge
- [ ] Mass / continuity
- [ ] Probability
- [ ] Local conservation laws
- [ ] Global conservation laws
- [ ] Flux-form conservation
- [ ] Noether correspondence

**Phase 7 status:** [~] Some conservation foundations exist; reusable generalized coverage remains.

---

# Phase 8 — Quantum Mechanics

- [ ] Complex vector spaces
- [ ] Hilbert-space states
- [ ] Operators
- [ ] Hermitian operators
- [ ] Eigenstates and eigenvalues
- [ ] Commutators
- [ ] Expectation values
- [ ] Uncertainty relations
- [ ] Schrödinger equation
- [ ] Stationary states
- [ ] Infinite square well
- [ ] Harmonic oscillator
- [ ] Tunneling
- [ ] Angular momentum
- [ ] Spin-1/2
- [ ] Pauli matrices
- [ ] Tensor products
- [ ] Time evolution
- [ ] Perturbation theory
- [ ] Density matrices

**Phase 8 status:** [ ] Not started.

---

# Phase 9 — Field Theory & Advanced Mathematical Physics

- [ ] Generalized field Euler-Lagrange equations
- [ ] Multiple interacting fields
- [ ] Noether currents
- [ ] Classical gauge fields
- [ ] Electromagnetism from an action
- [ ] Stress-energy tensors
- [ ] Selected classical field theories
- [ ] Advanced tensor calculus
- [ ] Selected mathematical structures useful for QFT

**Phase 9 status:** [~] Scalar-field variation foundation exists; broader field theory remains.

---

# Phase 10 — Formal Mathematics Coverage

## Lean-backed growth
- [ ] Arithmetic
- [ ] Polynomial identities
- [ ] Inequalities
- [ ] Finite sums / products
- [ ] Elementary functions
- [ ] Selected limits and calculus
- [ ] Linear algebra
- [ ] Selected mechanics identities
- [ ] Selected tensor identities
- [ ] Selected mathematical-physics theorems

**Phase 10 status:** [~] Lean proof path exists; formal coverage is being expanded gradually.

---

# Project Rules

- One coherent capability family is the normal delivery unit.
- Prefer real mathematical problems over infrastructure work.
- Each capability gets positive, negative, edge, and adversarial tests.
- Independent cross-checks are used where practical.
- AI output is untrusted until Automate verifies it.
- UNKNOWN/UNVERIFIED is a valid result and is never treated as success.
- A merged commit is not automatically a verified milestone.
- Exact merged-head CI is required before a capability is marked [x].
- This ledger is the project scoreboard and should be updated whenever the state changes.

## Next move

**1. Verify the current eigenproblem batch on its exact merged main SHA.**

**2. Expand Linear Algebra into inner products, norms, orthogonality, projections, and Gram-Schmidt.**

**3. Move into Phase 2A: Vector Calculus.**
