# Automate Mathematics & Physics Capability Roadmap

## Purpose

This roadmap makes mathematical and physical capability expansion the primary development program for Automate.

Automate already has a substantial verification substrate: typed mathematical and derivation IR, symbolic algebra/calculus, ODE verification, classical-mechanics/Lagrangian support, tensor/index and differential-geometry operations, bounded numerical ODE evidence, statistics, Lean integration, provenance, certificates, and a machine-agent contract.

The exact 50-problem acceptance campaign established the current baseline:

- 35 VERIFIED
- 10 UNSUPPORTED_SEMANTICS
- 1 UNVERIFIED
- 4 FAILED, intentionally representing incorrect claims

The next work therefore targets real capability gaps, especially linear algebra and electromagnetism/vector calculus.

## Guiding rule

> Build mathematics and physics, not infrastructure for its own sake.

A new abstraction, schema, adapter, registry field, or workflow component is justified only when it is required to represent, solve, cross-check, or honestly classify a concrete mathematical or physics problem.

Infrastructure is supporting work. It is not a milestone by itself.

## Capability maturity

A capability should progress through these states where applicable:

1. Represented: the canonical IR can express the mathematical object.
2. Applicable: a named rule and checker recognize the problem class.
3. Verified: representative positive cases produce evidence-backed verification.
4. Negative-tested: incorrect claims, malformed inputs, and edge cases fail closed.
5. Independently cross-checked: an independent implementation or backend agrees where practical.
6. AI-usable: the machine-agent contract exposes the capability.
7. Certified: durable certificates contain relevant evidence and provenance.

Code existing is not the definition of done.

---

# Phase 1 — Mathematical Foundations

Priority: P0

## 1A. Linear algebra

Build first because it underpins numerical physics, quantum mechanics, statistics, control, and many ordinary mathematical problems.

Target set:

- vectors and vector operations
- matrices and matrix operations
- matrix multiplication
- transpose and conjugate transpose
- determinant and trace
- inverse and rank
- linear systems Ax=b
- Gaussian elimination
- null space, row space, and column space
- basis, span, and linear independence
- change of basis
- eigenvalues and eigenvectors
- characteristic polynomial
- diagonalization
- symmetric and Hermitian matrices
- orthogonality
- norms and inner products
- projections and Gram-Schmidt
- positive-definite matrices
- quadratic forms

Verification should cover exact symbolic cases, shape/dimension rules, numerical cases, and assumption-aware invertibility/positivity.

## 1B. Core calculus

Expand beyond the current differentiation slice:

- limits and one-sided limits
- continuity
- indefinite and definite integration
- substitution
- integration by parts
- improper integrals
- Taylor and Maclaurin series
- convergence basics
- partial derivatives
- total differentials
- Jacobians and Hessians
- multivariable chain rule
- stationary points
- constrained optimization
- Lagrange multipliers

## 1C. General ODEs

Expand from solution-residual checking into reusable ODE families:

- separable first-order equations
- linear first-order equations
- Bernoulli and exact equations
- second-order constant-coefficient equations
- forced and damped oscillators
- coupled ODE systems
- autonomous systems
- initial-value problems
- boundary-value problems
- phase-space representations

---

# Phase 2 — Vector Calculus & Electromagnetism

Priority: P0

This phase directly closes the largest physics gap exposed by the acceptance campaign.

## 2A. Vector calculus

- scalar and vector fields
- gradient
- directional derivative
- divergence
- curl
- Laplacian
- Jacobians
- line integrals
- surface integrals
- volume integrals
- conservative fields and potentials
- flux
- Green theorem
- divergence theorem
- Stokes theorem

Support both local differential statements and integral statements, with differentiability, domain, and boundary assumptions explicitly represented.

## 2B. Electrostatics

- Coulomb law
- electric field
- electric potential
- point and continuous charge distributions
- Gauss law
- conductors
- capacitors
- dipoles
- electrostatic energy
- boundary conditions

## 2C. Magnetostatics

- Biot-Savart law
- Ampere law
- magnetic fields
- vector potential
- magnetic dipoles
- current distributions
- gauge conditions where represented

## 2D. Maxwell equations

- differential form
- integral form
- conversion between forms
- charge conservation
- continuity equation
- electromagnetic potentials
- Lorentz force
- Poynting vector and energy flow
- electromagnetic wave equation

## 2E. AI-usable compositions

Examples:

- derive E from a potential and verify its divergence
- compute flux and compare against enclosed charge
- derive a wave equation from Maxwell equations
- verify Lorentz-force expressions
- compare differential and integral forms under explicit assumptions

---

# Phase 3 — Advanced Calculus, PDEs, Waves & Expanded Mechanics

Priority: P1

## 3A. PDEs

- heat equation
- wave equation
- Laplace equation
- Poisson equation
- separation of variables
- initial and boundary conditions
- Fourier-series solutions
- Green-function methods where tractable

## 3B. Fourier and Laplace methods

- Fourier series
- Fourier transforms
- inverse transforms
- convolution
- Laplace transforms
- inverse Laplace transforms
- transform-based ODE solving

## 3C. Classical mechanics

Expand the existing Lagrangian foundation into:

- constraints
- holonomic and non-holonomic systems
- Lagrange multipliers
- cyclic coordinates
- generalized momentum
- Hamilton equations
- Poisson brackets
- canonical transformations
- phase space
- effective potentials
- central-force and Kepler problems
- coupled oscillators
- normal modes
- forced, damped, and resonant oscillators
- rigid-body motion
- inertia tensors
- Euler equations
- rotating frames
- Coriolis and centrifugal effects

## 3D. Waves and optics

- harmonic waves
- superposition
- interference
- standing waves
- dispersion
- phase and group velocity
- reflection and refraction
- Snell law
- polarization
- basic diffraction

---

# Phase 4 — Relativity, Geometry & Differential Forms

Priority: P1

The existing tensor and geometry system becomes the base for this phase.

## 4A. Tensor algebra completion

Implement real checker semantics for the currently registered tensor operations:

- index_contract
- raise_index
- lower_index

Then expand:

- arbitrary-rank tensors
- tensor addition and multiplication
- symmetrization and antisymmetrization
- Kronecker delta
- Levi-Civita symbol/tensor
- covariant derivatives
- metric compatibility
- coordinate transformations
- Lie derivatives

## 4B. Differential forms

- one-forms and p-forms
- wedge product
- exterior derivative
- pullback
- Hodge dual
- exterior-calculus identities

## 4C. Special relativity

- Lorentz transformations
- Minkowski metric
- proper time
- four-vectors
- four-velocity
- four-momentum
- invariant mass and energy relations
- four-current
- electromagnetic field tensor

## 4D. General relativity

Expand the current geometry support into:

- covariant derivatives
- curvature invariants
- stress-energy tensors
- Einstein field equations
- conservation laws
- Killing vectors
- geodesic deviation
- Schwarzschild spacetime
- weak-field and Newtonian limits
- gravitational redshift
- FLRW metrics
- Friedmann equations
- selected exact solutions

---

# Phase 5 — Thermodynamics & Statistical Physics

Priority: P1

## 5A. Thermodynamics

- state variables
- equations of state
- first law
- second law
- entropy
- enthalpy
- Helmholtz and Gibbs free energies
- thermodynamic potentials
- Maxwell relations
- Carnot cycle
- phase equilibrium
- ideal and selected nonideal gas models

## 5B. Statistical mechanics

- microstates and macrostates
- multiplicity
- Boltzmann distribution
- partition functions
- canonical ensemble
- grand canonical ensemble
- expectation values
- fluctuations
- entropy
- equipartition
- simple spin systems

---

# Phase 6 — Numerical Mathematics & Scientific Computing

Priority: P1

Extend the existing bounded numerical backend:

- numerical root finding
- nonlinear equation systems
- numerical differentiation
- numerical integration and quadrature
- interpolation
- optimization
- numerical linear algebra
- numerical eigenproblems
- FFT
- Monte Carlo
- parameter sweeps
- sensitivity analysis
- uncertainty propagation
- numerical PDE methods

Evidence levels must remain distinct:

NUMERICALLY_CHECKED is not automatically NUMERICALLY_CONVERGED, and neither is automatically a rigorous error bound.

Where practical, record tolerances, step sizes, convergence observations, conditioning, residual norms, solver configuration, and reproducibility data.

---

# Phase 7 — Approximation, Perturbation & Conservation

Priority: P1/P2

## 7A. Approximation

- Taylor expansion
- small-parameter expansion
- linearization
- asymptotic notation
- perturbation series
- weak-field approximation
- small-angle approximation
- nonrelativistic limits
- semiclassical limits

Automate must track assumptions that justify an approximation and must not silently treat an approximation as an exact identity.

## 7B. Conservation framework

Provide reusable verification for:

- energy
- linear momentum
- angular momentum
- charge
- mass and continuity
- probability
- local conservation laws
- global conservation laws
- flux-form conservation
- Noether correspondence

---

# Phase 8 — Quantum Mechanics

Priority: P2

Start after the mathematical foundations are sufficiently strong.

- complex vector spaces
- Hilbert-space states
- operators
- Hermitian operators
- eigenstates and eigenvalues
- commutators
- expectation values
- uncertainty relations
- Schrödinger equation
- stationary states
- infinite square well
- harmonic oscillator
- tunneling
- angular momentum
- spin-1/2
- Pauli matrices
- tensor products
- time evolution
- perturbation theory
- density matrices

Later: scattering, identical particles, entanglement, and quantum-information primitives.

---

# Phase 9 — Field Theory & Advanced Mathematical Physics

Priority: P2

Extend the existing scalar-field variation foundation into:

- generalized field Euler-Lagrange equations
- multiple fields
- Noether currents
- classical gauge fields
- electromagnetism from an action
- stress-energy tensors
- selected classical field theories
- advanced tensor calculus
- selected mathematical structures useful for quantum field theory

---

# Phase 10 — Formal Mathematics Coverage

Priority: P2

Grow Lean-backed proof coverage through reusable layers:

1. arithmetic
2. polynomial identities
3. inequalities
4. finite sums and products
5. elementary functions
6. selected limits and calculus
7. linear algebra
8. selected mechanics identities
9. selected tensor identities
10. selected mathematical-physics theorems

Formal proof is one evidence class. It is not a requirement that every numerical or empirical statement become a theorem.

---

# External Research & Reuse Policy

Before reimplementing substantial mathematics:

1. Audit the current Automate implementation and rule registry.
2. Search mature open-source implementations and scientific libraries.
3. Prefer safe composition or adaptation of established algorithms over needless reinvention.
4. Check licenses and redistribution compatibility before copying or importing code.
5. Use independent implementations for cross-checks where practical.
6. Keep Automate's canonical semantics independent of any single package.

Potential reference ecosystems include SymPy, NumPy, SciPy, mpmath, EinsteinPy, Pint, and established numerical, symbolic, PDE, geometry, and scientific-computing projects.

External packages are references and bounded execution backends, not authorities. Evidence still needs Automate status classification and provenance.

---

# Capability Development Workflow

## 1. Choose one bounded capability family

Examples: linear algebra, vector calculus, electromagnetism, general ODEs, or tensor index operations.

Avoid vague tasks such as "improve maths."

## 2. Define the real problem matrix before coding

Each batch should contain representative:

- positive cases
- negative cases
- edge cases
- assumption/domain cases
- compositions with existing capabilities
- independent cross-check cases where practical

The problem matrix is the acceptance target.

## 3. Audit current code and research existing work

Inspect current representations, rules, backends, tests, and agent contracts. Research established implementations before designing a parallel solution.

## 4. Implement a vertical slice

Prefer:

representation → rule → checker → evidence → tests → agent exposure

Do not create infrastructure merely because a future version might need it.

## 5. Test adversarially

Every capability batch must contain deliberately incorrect claims.

A false claim being rejected is expected behavior. A false claim being accepted is a defect.

## 6. Independently cross-check

Where practical, compare Automate's result against another implementation or backend on the same mathematical claim.

Independence must be real, not merely a second call to the same engine.

## 7. Update the machine-agent contract once per capability batch

Batch changes to the capability catalog, rule registry, context/proposal documentation, and examples.

Do not touch the agent contract for every helper function.

## 8. Run a named acceptance campaign

Every completed capability batch receives a named problem suite using:

VERIFIED
UNVERIFIED
UNSUPPORTED_SEMANTICS
FAILED

The suite must demonstrate honest classification, not merely a high pass count.

## 9. Complete documentation and certificates

Document semantics, assumptions, supported forms, known limits, backends, and evidence. Confirm certificate/provenance output is sufficient for an external AI agent to understand what was actually checked.

## 10. Consolidate before merge

Preferred unit:

one coherent capability family → one feature branch → one reviewable PR → squash merge

Small local commits are acceptable during implementation. The main branch should receive meaningful capability milestones, not a commit for every helper function, typo, test tweak, or debug step.

Do not create a separate PR for every trivial function when it belongs to the same capability family.

## 11. Verify the exact merged head

After merge:

1. record the resulting main SHA;
2. verify authoritative CI for that exact SHA;
3. inspect the capability acceptance results;
4. only then mark the capability milestone complete.

Never use an older green commit as evidence for a newer main commit.

---

# Capability Batch Size

A batch should be large enough to deliver a usable mathematical family, for example:

- linear algebra core
- linear algebra eigen/inner-product extension
- vector calculus core
- electrostatics
- magnetostatics and Maxwell
- general ODE families
- PDE/Fourier
- tensor-index completion
- differential forms
- special relativity

Avoid thousands of microscopic PRs. Prefer fewer coherent milestones with substantial acceptance suites.

---

# Definition of Done

A capability family is complete when:

- real problems can be represented;
- applicable rules are registered;
- a checker produces evidence;
- assumptions and domains are respected;
- false or malformed claims fail closed;
- representative tests pass;
- negative tests pass;
- an independent cross-check is used where practical;
- numerical claims record meaningful tolerances and provenance;
- the AI agent contract exposes the capability;
- the semantic boundary is documented;
- a capability acceptance campaign passes;
- exact-head CI verifies the merged milestone.

"Implemented" alone is not "done."

---

# Current Baseline and Immediate Order

| Area | State |
|---|---|
| Symbolic algebra | Working |
| Basic calculus | Working |
| ODE residual verification | Working foundation |
| Classical mechanics | Working foundation |
| Tensor/index validation | Working foundation |
| Differential geometry/GR | Working foundation |
| Numerical ODEs | Working foundation |
| Statistics | Working foundation |
| Lean formal path | Working foundation |
| Linear algebra | Core batch verified; eigenproblem extension in progress |
| Vector calculus | NEXT MAJOR GAP |
| Electromagnetism | NEXT MAJOR GAP |
| General ODE families | EXPANSION TARGET |
| Tensor raise/lower/contract | IMMEDIATE TENSOR EXPANSION |
| PDE/Fourier | Planned |
| Thermodynamics/statistical mechanics | Planned |
| Quantum mechanics | Planned |

Immediate execution order:

**Phase 1A — Linear Algebra Core — completed on main**

then

**Phase 1A — Eigenvalues, eigenvectors, characteristic polynomial, diagonalization**

then

**Phase 2A — Vector Calculus**

then

**Phase 2B–2D — Electromagnetism**

then

**Phase 1B/1C + Phase 3 — General ODE, advanced calculus, PDE/Fourier**

then continue through the remaining phases in dependency order.

The order may change when real workload testing exposes a better dependency chain, but infrastructure should not displace capability work without a demonstrated technical reason.
