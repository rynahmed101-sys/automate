# Automate Development Stages & Capability Ledger

This is the single authoritative roadmap for Automate's mathematical and physics development.

It replaces the old split between a domain/capability phase ladder and a separate development-intelligence roadmap. **Development stage and capability scope are now one system.**

The purpose is not to accumulate isolated rules. Automate should progressively become a general mathematical-physics reasoning engine whose capabilities deepen as each stage advances.

## Core development principle

A domain is developed **breadth-first and depth-first enough to become reusable** before Automate treats that domain as mature.

For example, introducing calculus does not mean implementing only first derivatives and one integral. The calculus machinery must support the natural generalization of the domain: arbitrary derivative order where mathematically defined, repeated differentiation/integration where represented, symbolic and numeric forms, multivariable forms when in scope, composition with other operators, domain/assumption handling, and failure cases.

Likewise, a later physics example must reuse the earlier mathematical machinery instead of receiving a one-off special-case rule.

This prevents the project from becoming a large collection of impressive-looking calculators that are difficult to reason about, extend, or trust.

## The universal capability ladder

Every capability family introduced at any stage is developed through the same ladder:

1. **Representation** — typed, explicit mathematical objects and their valid shapes/domains.
2. **Primitive operations** — the elementary operations of the domain, including natural higher-order/generalized forms.
3. **Composition** — operations can be chained and nested rather than working only as isolated calls.
4. **Assumptions and domains** — conditions, singularities, parameter restrictions, dimensions, orientations, boundary conditions, and conventions are explicit.
5. **Derivation / verification** — Automate can verify results and, where the architecture supports it, construct derivation chains from trusted operations.
6. **Generalization** — avoid arbitrary low ceilings such as “only first/second/fourth order” when a general representation is practical.
7. **Failure intelligence** — malformed, ambiguous, unsupported, unsafe, or insufficiently justified claims fail closed as UNKNOWN/UNVERIFIED rather than being guessed.
8. **Independent evidence** — symbolic, numerical, structural, dimensional, or formal cross-checks are used where appropriate.
9. **Adversarial coverage** — positive, negative, boundary, degenerate, and adversarial cases are tested.
10. **Cross-domain reuse** — later capabilities must consume the earlier domain machinery instead of duplicating it.
11. **Certification** — registry/schema/catalog integration, documentation, focused tests, regression tests, Exact-head verification, and Security Audit are completed before the capability is marked verified.

A capability is not considered mature merely because one formula or named example works.

## External research and reuse policy

Before substantial mathematical reimplementation:

1. Audit current representations, rules, backends, tests, and contracts.
2. Research mature scientific/open-source implementations.
3. Prefer safe composition or bounded backend use where appropriate.
4. Check licensing before copying or importing code.
5. Use independent implementations for cross-checks where practical.
6. Keep Automate's canonical semantics independent of any single external package.

External libraries are references/backends, not authorities. Their output still requires Automate's evidence classification and provenance.

## Capability-batch definition of done

A coherent capability family is complete only when, as applicable:

- real problems can be represented;
- a named rule/checker applies;
- evidence is produced;
- assumptions/domains are respected;
- false or malformed claims fail closed;
- positive, negative, edge, and adversarial tests exist;
- independent cross-checking is performed where practical;
- the machine-agent contract exposes the capability;
- semantic boundaries are documented;
- a named acceptance campaign records honest classifications;
- provenance/certificate requirements are satisfied;
- the feature is merged through the normal reviewable PR boundary;
- authoritative Exact-head verification passes for the exact merged main SHA;
- relevant Security Audit evidence is available.


## Capability maturity inherited from the existing roadmap

For each capability family, the development ladder must preserve these distinct maturity states:

1. **Represented** — canonical IR can express the mathematical object.
2. **Applicable** — a named rule/checker recognizes the problem class.
3. **Verified** — representative positive cases produce evidence-backed verification.
4. **Negative-tested** — incorrect claims, malformed inputs, and edge cases fail closed.
5. **Independently cross-checked** — an independent implementation or route agrees where practical.
6. **AI-usable** — the machine-agent contract exposes the capability.
7. **Certified** — durable provenance/certificate evidence exists and the exact merged main milestone has passed the authoritative verification boundary.

These states must never be silently collapsed. A capability can be implemented and tested while still remaining uncertified.


## Development-stage rules

- Work on the **earliest incomplete stage** unless a prerequisite defect blocks it.
- Within a stage, finish the current capability family before opening unrelated later-stage work.
- A new domain must first establish its reusable representation and general primitive machinery.
- Named examples are acceptance cases, not the architecture itself.
- Do not create artificial order/dimension limits unless there is a documented mathematical, safety, or computational reason.
- Reuse earlier machinery whenever possible.
- Existing later-stage work may be preserved, repaired, and certified, but new development should follow the earliest incomplete stage.
- UNKNOWN/UNVERIFIED is a valid result.
- Never mark a capability [x] until authoritative verification exists.
- Exact-head CI and Security Audit remain authoritative and must not be weakened, disabled, or bypassed.

## Status key

- [ ] Not started
- [~] In progress
- [!] Implemented/merged but authoritative verification is still pending
- [x] Completed and authoritatively verified

---

# Stage 1 — Complete Core Mathematical Engine

**Goal:** Build a broad, reusable mathematical foundation before Automate moves into increasingly specialized physics.

This stage contains the mathematical basics that later physics must be able to rely on. The standard is not “a few textbook examples”; it is reusable general machinery.

## 1A. Linear algebra

- [x] Core vectors and vector operations
- [x] Matrices, shapes, multiplication, transpose
- [x] Determinant, trace, inverse, rank
- [x] Gaussian elimination, RREF, unique Ax=b solving
- [x] Characteristic polynomial
- [x] Eigenvalues with multiplicity
- [x] Eigenvector verification
- [x] Diagonalization
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
- [~] Moore-Penrose pseudoinverse and least-squares solutions
- [~] Complex scalar/vector/matrix semantics needed by later quantum and spectral reasoning

**Depth rule:** vector/matrix operations should be dimension-generic where represented; subspace and basis operations must correctly handle rectangular, rank-deficient, zero-dimensional, symbolic, and degenerate cases.

## 1B. Calculus

- [ ] Limits and continuity
- [ ] Derivatives and higher-order derivatives
- [ ] Chain/product/quotient and implicit differentiation
- [ ] Higher-order symbolic differentiation without arbitrary order ceilings
- [ ] Definite and indefinite integration
- [ ] Repeated/nested integration where represented
- [ ] Substitution, integration by parts, partial fractions, trigonometric and other general integration techniques where tractable
- [ ] Fundamental theorem of calculus
- [ ] Improper integrals and convergence-aware handling
- [ ] Taylor / Maclaurin series and higher-order expansions
- [ ] Partial derivatives and total differentials
- [ ] Higher-order partial derivatives
- [ ] Jacobians and Hessians
- [ ] Multivariable chain rule
- [ ] Stationary points and constrained optimization
- [ ] Domain/singularity/assumption-aware calculus

**Depth rule:** “derivative” means a general differentiation capability, not a permanently hard-coded first-derivative feature. The same principle applies to integrals, series order, and multivariable operations.

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

**Current status:** [~] Active. Current main exact-head verification and Security Audit both pass for SHA `1b9b4f2745eefa0c8a74b514871053b8f9549898`. The merged Stage 1A linear-algebra baseline, including change-of-basis, quadratic forms, and SVD, is therefore authoritatively verified on the exact current main SHA `1b9b4f2745eefa0c8a74b514871053b8f9549898`. Moore-Penrose pseudoinverse/least-squares and complex semantics remain implementation/reconciliation work on open branches. Stage 1B calculus and Stage 1C ODE foundations remain unfinished.

---

# Stage 2 — Core Mathematical Physics

**Goal:** Apply the Stage 1 engine across the central continuous-mathematics and classical-physics domains.

## 2A. Vector calculus and fields

- [x] Scalar/vector fields
- [x] Gradient
- [x] Directional derivative
- [x] Divergence
- [x] Curl
- [x] Laplacian
- [x] Line/surface/volume integrals
- [x] Green's theorem
- [x] Divergence theorem
- [x] Stokes' theorem
- [ ] General coordinate-aware field operations where supported
- [ ] Conservative fields and potential reconstruction at broader scope

## 2B. PDEs and transforms

### PDE representation and verification foundation
- [ ] Explicit PDE independent-variable representation
- [ ] Explicit PDE parameter representation
- [ ] Candidate-solution substitution and symbolic residual construction
- [ ] Generic PDE residual verification
- [ ] Fail-closed handling of malformed, unsupported, or unresolved PDE claims
- [ ] PDE domain / singularity / assumption handling
- [ ] Heat equation verification
- [ ] Wave equation verification
- [ ] Laplace / Poisson equation verification

### PDE solution methods
- [ ] Initial conditions
- [ ] Boundary conditions
- [ ] Initial-boundary-condition validation and compatibility
- [ ] Separation of variables
- [ ] Separated-mode construction and verification
- [ ] PDE solution reconstruction from separated modes
- [ ] Green-function methods where tractable
- [ ] Green-function representation and residual verification
- [ ] PDE method/domain failure intelligence

### Fourier-series machinery
- [ ] Fourier-series canonical representation
- [ ] Period and interval conventions
- [ ] Fourier-series coefficient computation
- [ ] Fourier-series reconstruction
- [ ] Fourier-series coefficient/reconstruction verification
- [ ] Convergence / validity conditions for Fourier series
- [ ] Fourier-series boundary/initial-data use in PDE solutions

### Fourier-transform machinery
- [ ] Explicit Fourier transform convention representation
- [ ] Fourier transforms
- [ ] Inverse Fourier transforms
- [ ] Fourier transform-pair verification
- [ ] Transform-domain assumptions and convergence handling
- [ ] Fail-closed unresolved transform evaluation

### Convolution machinery
- [ ] Continuous convolution representation
- [ ] Convolution evaluation
- [ ] Convolution verification
- [ ] Convolution theorem
- [ ] Convolution-theorem verification
- [ ] Convolution-domain / convergence assumptions

### Laplace-transform machinery
- [ ] Explicit Laplace transform convention representation
- [ ] Laplace transforms
- [ ] Inverse Laplace transforms
- [ ] Laplace transform-pair verification
- [ ] Transform-domain assumptions and convergence handling
- [ ] Fail-closed unresolved inverse-transform evaluation

### Cross-cutting transform/PDE integration
- [ ] Composition of transforms with PDE representations
- [ ] Independent cross-checks for transform and PDE results
- [ ] Machine-agent exposure of transform/PDE capabilities
- [ ] Named acceptance campaigns covering positive, negative, boundary, degenerate, and adversarial cases

## 2C. Classical mechanics

- [ ] Kinematics and dynamics
- [ ] Work, energy, and momentum
- [x] Constraints and Lagrange multipliers
- [x] Lagrangian mechanics
- [x] Hamilton equations
- [ ] Poisson brackets
- [ ] Canonical transformations
- [ ] Central-force / Kepler problems
- [ ] Coupled oscillators and normal modes
- [ ] Rigid-body motion
- [ ] Rotating frames

## 2D. Electromagnetism

- [x] Point-charge force/field/potential foundations
- [x] Charge distributions
- [x] Bounded continuous-charge kernels
- [x] Finite uniform line-charge potential
- [x] Gauss law
- [x] Conductors and capacitors
- [x] Dipole potential and electric-field verification
- [ ] Dipole electrostatic energy
- [ ] Electrostatic boundary conditions
- [ ] Biot-Savart law
- [ ] Ampere law
- [ ] Magnetic fields
- [ ] Vector potential
- [ ] Magnetic dipoles
- [ ] Gauge conditions where represented
- [x] Differential Maxwell equations
- [ ] Integral Maxwell equations
- [ ] Differential ↔ integral consistency
- [ ] Charge conservation
- [ ] Electromagnetic potentials
- [x] Lorentz force
- [x] Poynting vector
- [ ] Electromagnetic wave equation

## 2E. Waves and optics

- [ ] Harmonic waves
- [ ] Superposition and interference
- [ ] Standing waves
- [ ] Dispersion
- [ ] Reflection / refraction
- [ ] Polarization
- [ ] Basic diffraction

**Stage 2 exit condition:** core mathematical-physics operators and equations must be composable with Stage 1 mathematics. Special-case physics rules must not substitute for missing general mathematics.

**Current status:** [~] Existing vector-calculus and electrostatic work is preserved, but Stage 1 takes priority until complete.

---

# Stage 3 — Numerical, Approximate & Scientific Reasoning

**Goal:** Teach Automate how exact mathematics, approximation, and numerical evidence relate.

## 3A. Numerical mathematics

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

## 3B. Controlled approximation

- [ ] Taylor expansion as controlled approximation
- [ ] Small-parameter expansion
- [ ] Linearization
- [ ] Asymptotic notation
- [ ] Perturbation series
- [ ] Weak-field approximation
- [ ] Small-angle approximation
- [ ] Nonrelativistic limits
- [ ] Semiclassical limits

## 3C. Scientific evidence

- [ ] Distinguish exact, approximate, and numerical claims
- [ ] Track error/residual evidence
- [ ] Detect conditioning and instability
- [ ] Compare independent computational routes
- [ ] Preserve assumptions behind approximations

**Stage 3 exit condition:** numerical evidence must supplement exact reasoning rather than silently replace it.

---

# Stage 4 — Geometry, Tensors & Relativity

**Goal:** Generalize the mathematical representation from vectors/matrices/fields to coordinate-aware geometry.

## 4A. Tensor algebra

- [ ] Tensor index contraction
- [ ] Raise/lower indices
- [ ] Arbitrary-rank tensor operations
- [ ] Symmetrization / antisymmetrization
- [ ] Kronecker delta
- [ ] Levi-Civita symbol/tensor
- [ ] Covariant derivatives
- [ ] Metric compatibility
- [ ] Coordinate transformations
- [ ] Lie derivatives

## 4B. Differential forms

- [ ] One-forms and p-forms
- [ ] Wedge product
- [ ] Exterior derivative
- [ ] Pullback
- [ ] Hodge dual
- [ ] Exterior-calculus identities

## 4C. Relativity

- [ ] Lorentz transformations
- [ ] Minkowski metric
- [ ] Proper time
- [ ] Four-vectors
- [ ] Four-momentum
- [ ] Four-current
- [ ] Electromagnetic field tensor
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

**Stage 4 exit condition:** coordinate changes, index operations, and geometric representations must be general reusable machinery, not isolated relativity formulas.

---

# Stage 5 — Thermodynamics & Statistical Physics

**Goal:** Develop state-based, ensemble-based, and probabilistic physical reasoning.

## 5A. Thermodynamics

- [ ] State variables and equations of state
- [ ] First law
- [ ] Second law
- [ ] Entropy
- [ ] Enthalpy
- [ ] Helmholtz / Gibbs free energies
- [ ] Maxwell relations
- [ ] Carnot cycle
- [ ] Phase equilibrium

## 5B. Statistical mechanics

- [ ] Microstates / macrostates
- [ ] Multiplicity
- [ ] Boltzmann distribution
- [ ] Partition functions
- [ ] Canonical ensemble
- [ ] Grand canonical ensemble
- [ ] Expectation values and fluctuations
- [ ] Equipartition
- [ ] Simple spin systems

**Stage 5 exit condition:** Automate must track state variables, constraints, ensemble assumptions, and derived quantities consistently.

---

# Stage 6 — Quantum Mechanics

**Goal:** Extend the engine into complex vector spaces, operators, states, and probabilistic measurement.

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

**Depth rule:** quantum capabilities must reuse and extend the general linear-algebra, calculus, ODE, numerical, and approximation machinery instead of creating parallel one-off implementations.

---

# Stage 7 — Field Theory & Advanced Mathematical Physics

**Goal:** Move from finite-dimensional and single-system reasoning toward fields, actions, symmetries, and interacting systems.

- [ ] Generalized field Euler-Lagrange equations
- [ ] Multiple interacting fields
- [ ] Noether currents
- [ ] Classical gauge fields
- [ ] Electromagnetism from an action
- [ ] Stress-energy tensors
- [ ] Selected classical field theories
- [ ] Advanced tensor calculus
- [ ] Selected mathematical structures useful for QFT

**Stage 7 exit condition:** field-theoretic operations must compose with the tensor, calculus, variational, symmetry, and conservation machinery already developed.

---

# Stage 8 — Cross-Domain Synthesis

**Goal:** Stop treating mathematics and physics as isolated namespaces and make Automate reason across them.

Target capabilities include:

- [ ] Mathematics → physics derivation chains
- [ ] Physics → required mathematics selection
- [ ] Reuse of the same mathematical object across domains
- [ ] Dimensional and unit consistency
- [ ] Assumption propagation across multi-step derivations
- [ ] Method selection from problem structure
- [ ] Multiple independent solution routes
- [ ] Counterexample generation for candidate claims
- [ ] Exact ↔ numerical ↔ formal evidence comparison
- [ ] Automatic detection of insufficient premises
- [ ] Long derivation-chain provenance
- [ ] Cross-domain regression corpus

**Stage 8 exit condition:** Automate should increasingly choose and compose appropriate existing machinery rather than requiring a special rule for each new problem.

---

# Stage 9 — Formal Mathematics & Proof Escalation

**Goal:** Turn selected mathematical reasoning into machine-checked proof where practical.

**Ordering rule:** This stage is a formal-evidence escalation layer, not a prerequisite barrier for earlier mathematical or physics stages. Formalization should be applied capability-by-capability whenever the IR and semantics support faithful translation; Stage 9 collects the broader formalization frontier after the core capability families have matured.

## Lean-backed growth

Formal-proof work may begin before this stage when an earlier capability has a faithful formal boundary. A later Stage 9 item must not be used as justification for postponing useful formal evidence that is already technically supported.

- [ ] Arithmetic
- [ ] Polynomial identities
- [ ] Inequalities
- [ ] Finite sums / products
- [ ] Elementary functions
- [ ] Selected limits and calculus
- [ ] Linear algebra
- [ ] Selected mechanics identities
- [ ] Tensor identities
- [ ] Selected mathematical-physics theorems

Additional reasoning goals:

- [ ] Decide when a claim is suitable for formal escalation
- [ ] Preserve correspondence between Automate IR and formal proof terms
- [ ] Distinguish “symbolically verified” from “formally proved”
- [ ] Maintain proof provenance

**Stage 9 exit condition:** formal proof is an evidence layer integrated with reasoning, not a disconnected collection of demonstrations.

---

# Stage 10 — Research-Grade Mathematical-Physics Reasoning

**Goal:** Make Automate useful not merely as a calculator or verifier, but as a structured scientific reasoning system.

Target capabilities:

- [ ] Problem decomposition
- [ ] Representation selection
- [ ] Method selection
- [ ] Hypothesis formation
- [ ] Symbolic derivation
- [ ] Numerical experiment design
- [ ] Counterexample search
- [ ] Assumption discovery
- [ ] Competing-derivation comparison
- [ ] Uncertainty and evidence assessment
- [ ] Literature/formal-result integration where supported
- [ ] Reproducible derivation provenance
- [ ] Research-problem templates
- [ ] Human-review checkpoints for genuinely ambiguous mathematics

**Stage 10 exit condition:** Automate should be able to approach a mathematical-physics problem by selecting representations and methods, deriving candidate results, checking them independently, identifying uncertainty or missing assumptions, and presenting an auditable chain of reasoning.

---

# How future agents must use this ledger

When entering a new chat:

1. Read this file first.
2. Identify the **earliest incomplete Development Stage**.
3. Identify the earliest incomplete capability family inside that stage.
4. Inspect existing implementation before adding anything.
5. Extend the general machinery before adding more examples.
6. Reuse earlier-stage primitives.
7. Add positive, negative, boundary, degenerate, and adversarial tests.
8. Add independent mathematical/numerical/formal cross-checks where appropriate.
9. Update registry/schema/catalog and documentation.
10. Run focused and regression tests.
11. Commit through a coherent PR.
12. Merge only when appropriate.
13. Wait for Development CI.
14. Wait for authoritative Exact-head verification.
15. Wait for Security Audit.
16. Mark [x] only after authoritative evidence.
17. If this ledger itself changes, the resulting main HEAD must pass the authoritative gates again.
18. Then continue to the next incomplete capability.

## Anti-patterns explicitly prohibited

- Do not jump to a later stage because it contains a more exciting physics problem while an earlier mathematical foundation is incomplete.
- Do not implement “fourth derivative” as a special feature if a general n-th derivative representation is practical.
- Do not implement a physics formula as a one-off calculator when its mathematical operators should exist generally.
- Do not create arbitrary dimension/order ceilings without documenting why.
- Do not duplicate mathematical machinery inside physics modules.
- Do not treat a green unit test for one example as proof of a general capability.
- Do not weaken Exact-head CI, Security Audit, parser restrictions, or fail-closed semantics to accelerate development.
- Do not update a capability to [x] based solely on a merge, local tests, or an unverified CI observation.

## Current project position

**Active development stage:** Stage 1 — Complete Core Mathematical Engine.

**Current priority:** finish the remaining Stage 1 linear-algebra families and then build the core calculus and ODE machinery to the same generality standard.

**Important:** existing Phase 2+ implementation is not discarded. It remains part of the codebase and will be reused and brought into this staged ladder when its prerequisites are mature.

**Current authoritative baseline:** the current `main` HEAD. The latest merged Stage 2C and Stage 2D implementation passes are present on main but remain `[!]` until authoritative Exact-head verification and Security Audit evidence exist for the exact current HEAD. The ledger must not claim certification for capabilities that are only present on unmerged branches.

---

## Delegated implementation queue

The primary agent owns repository ground work, reconciliation, defect repair, certification bookkeeping, and this ledger. Other AIs may implement isolated capability families, but their branches are not authoritative until reconciled and certified on merged main.

- Stage 1A linear-algebra branches remain delegated implementation/review work and must be reconciled against the current main before certification.
- PR #82 — Stage 2C completion: merged to main; constraints/Lagrange multipliers, Lagrangian mechanics, and Hamilton-equation verification are now `[x]` after exact-head/security verification of current main.
- PR #83 — Stage 2D completion: merged to main; differential Maxwell equations, Lorentz force, and Poynting-vector/energy-balance verification are now `[x]` after exact-head/security verification of current main.
- Existing Stage 2B/Stage 2C/Stage 2D branches that predate the current main may be stale; do not blindly merge them.

These delegated branches may be stale. Do not blindly rebase or duplicate their work. Reconcile each against the current main only when it reaches the review queue. The earliest incomplete Stage 1A capability remains the controlling priority.

---

## Project quality contract

Automate is intended to become a **general, progressively verified mathematical-physics reasoning engine**, not a pile of calculators.

Every new feature should answer four questions:

1. **What general mathematical capability does this add?**
2. **What existing capability does it reuse?**
3. **What broader class of problems does it unlock?**
4. **How do we independently know that it is correct?**

If the answer to the first question is merely “this one formula now works,” the implementation probably belongs one abstraction level too low.


## Implementation-state companion

The phase ledger remains the sole authority for roadmap ordering and completion markers. Implementation ownership, branch/PR location, reconciliation state, dependency links, and verification evidence are tracked separately in `docs/CAPABILITY_INVENTORY.json`. Agents must not infer implementation state from the presence or absence of code on `main` alone.
