# Automate Project Phase Ledger

This is the human-readable project scoreboard for the Maths & Physics capability program.

The ledger is maintained by the project lead/engineering agent. It records project state in plain English.

The recorded capability baseline identifies the last substantive main milestone; ledger-only bookkeeping commits do not need to replace that baseline.

## Status key

- [ ] Not started
- [~] In progress
- [!] Verification pending
- [x] Completed and verified

A merged feature is **not** marked [x] until its acceptance evidence and exact-head CI verification are complete.

## Current position

**Last recorded capability baseline main:** `bb43131730ecc56797870ca369695275e32f0427`

**Current work:** Phase 2A Vector Calculus through integral identities is completed and exactly verified. Phase 2B point-charge electrostatics, bounded continuous-charge kernels, and finite uniform line-charge potential are now certified on main. The next bounded electrostatics batch is Gauss-law verification.

**Latest authoritative verification:** Exact-head Python 3.10/3.11/3.12/3.13, full tests, adversarial tests, the exact 50-problem acceptance campaign, Phase 1A Linear Algebra Core/Eigenproblem campaigns, Lean 4, CodeQL, and pip-audit passed on merged main SHA `bb43131730ecc56797870ca369695275e32f0427`.

**Next capability:** Gauss-law verification for explicit bounded Cartesian charge/surface configurations. Conductors, capacitors, dipoles, and general boundary conditions remain later bounded batches.

---

# Phase 1 — Mathematical Foundations

## Linear Algebra
- [x] Core vectors and vector operations
- [x] Matrices, shapes, multiplication, transpose
- [x] Determinant, trace, inverse, rank
- [x] Gaussian elimination, RREF, unique Ax=b solving
- [x] Characteristic polynomial
- [x] Eigenvalues with multiplicity
- [x] Eigenvector verification
- [x] Diagonalization
- [ ] Null space, row space, column space
- [ ] Basis, span, linear independence
- [ ] Change of basis
- [ ] Symmetric / Hermitian matrices
- [x] Norms, inner products, orthogonality
- [x] Projections and Gram-Schmidt
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

**Phase 1 status:** [x] Core Phase 1 Linear Algebra milestones through inner products, projections, and Gram-Schmidt are verified; null spaces/bases and matrix-structure expansions remain.

---

# Phase 2 — Vector Calculus & Electromagnetism

## Vector Calculus
- [x] Scalar and vector fields
- [x] Gradient
- [x] Directional derivative
- [x] Divergence
- [x] Curl
- [x] Laplacian
- [x] Line / surface / volume integrals
- [x] Green's theorem / divergence theorem / Stokes' theorem
- [x] Coulomb force / point-charge field / point-charge potential
- [x] Conservative fields and potentials
- [x] Flux / surface-flux capability
- [x] Green's theorem
- [x] Divergence theorem
- [x] Stokes' theorem

## Electrostatics
- [ ] Coulomb law
- [ ] Electric field and potential
- [x] Charge distributions
- [x] Bounded continuous-charge field/potential kernels
- [x] Finite uniform line-charge potential
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

**Phase 2 status:** [~] Vector Calculus through integral identities and Phase 2B point-charge, bounded continuous-charge, and finite line-charge potential batches are verified. Gauss-law verification is the next bounded electrostatics capability.

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

**1. Implement bounded Gauss-law verification for explicit Cartesian charge/surface configurations.**

**2. Verify enclosed-charge/flux equivalence with positive, negative, geometry-edge, and adversarial cases.**

**3. Preserve the explicit geometry and fail-closed semantics before advancing to conductors/capacitors or broader electrostatics.**
