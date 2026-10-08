# Automate Scientific Engine Ledger
Version: 1.0
Established: 2026-10-09
Authority: this file is the sole sequencing and certification authority for Automate's mathematics/physics engine.

## 1. Mission

Automate is a first-class AI-compatible scientific mathematics and physics engine.

Its responsibility is:
- mathematical representation and computation
- symbolic and numerical reasoning
- physics derivation and verification
- explicit assumptions and domains
- independent cross-checks
- machine-readable evidence and provenance
- fail-closed AI-facing scientific contracts

Automate is NOT an autonomous software-development controller. Repository mutation, worker supervision, autonomous repair, and development orchestration are outside this engine's mandate.

## 2. Authority model

This ledger replaces the previous phase-ledger/roadmap split.

Authoritative sources:
1. This ledger: sequencing, capability status, certification state, and operating procedure.
2. Actual source code and tests: implementation evidence.
3. GitHub Actions on the exact relevant commit: CI/security evidence.
4. `docs/CAPABILITY_INVENTORY.json`: implementation-location and evidence index only. It cannot override this ledger.

Reference material may inform implementation but cannot override this ledger.

The former `docs/PROJECT_PHASE_LEDGER.md` and `docs/MATH_PHYSICS_ROADMAP.md` are obsolete and must not be used for sequencing.

## 3. Scientific trust model

Never collapse these states:

implemented
→ locally tested
→ CI verified
→ independently cross-checked
→ formally proved
→ certified

A capability is [x] only when its required evidence exists and the exact merged main commit has passed the authoritative verification boundary.

Preferred failure states:
- invalid
- malformed
- unsupported
- ambiguous
- failed
- unverifiable
- disagreement

False negatives are preferable to plausible unsupported answers.

Backend output is evidence, not proof. Agreement between independent systems is evidence, not proof. Formal proof is distinct.

## 4. Universal capability contract

Every meaningful capability must establish, as applicable:
1. canonical representation
2. semantic validation
3. explicit inputs, variables, domains, and assumptions
4. computation/derivation
5. verification
6. failure behavior
7. evidence/provenance
8. machine-readable contract
9. positive tests
10. negative tests
11. malformed/edge/adversarial tests
12. independent cross-check where practical
13. documentation
14. focused and regression CI
15. exact-head/security evidence before certification

Do not create one-off physics calculators where reusable mathematics belongs underneath them.

## 5. Development rule

Always work on the earliest incomplete capability in the earliest incomplete stage unless a defect blocks it.

Existing later-stage code is preserved, but does not automatically become the next development target.

Mature external engines should be reused where appropriate:
- SymPy
- NumPy
- SciPy
- EinsteinPy
- Lean 4 / Mathlib

Automate supplies semantic contracts, verification, evidence, provenance, and cross-domain composition around them.

## 6. Current state

Authoritative main:
`e966cc286565c18356aca9a8d2f367c2db901fca`

Current active frontier:
Stage 1B multivariable calculus.

Immediate sequence:
1. partial derivatives
2. total differentials
3. higher-order partial derivatives
4. Jacobians
5. Hessians
6. multivariable chain rule
7. multivariable Taylor expansion
8. domain/assumption propagation
9. stationary points and extrema
10. constrained extrema / Lagrange multipliers
11. ODE foundation
12. numerical mathematics/evidence

The order may move only when repository evidence establishes a prerequisite defect or shows that a supposedly missing capability is already genuinely complete.

## 7. Stage ladder

### Stage 1 — Core Mathematics
1A Linear algebra
- vectors/matrices and core operations
- linear systems
- eigenproblems
- subspaces/bases
- inner products/norms
- quadratic forms
- SVD/pseudoinverse
- complex linear algebra

1B Calculus
- limits/continuity
- differentiation
- integration
- series
- multivariable calculus
- optimization
- domains/assumptions

1C ODEs
- first-order families
- higher-order linear equations
- coupled systems
- IVPs/BVPs
- candidate-solution verification
- domain/condition validation

Stage 1 exits only when its reusable mathematics is strong enough to support later physics without repeated foundational backfill.

### Stage 2 — Core Mathematical Physics
- vector calculus and fields
- PDE representation and verification
- transforms and convolution
- classical mechanics
- electromagnetism
- waves and optics

### Stage 3 — Numerical and Approximate Mathematics
- roots and nonlinear systems
- differentiation/integration
- interpolation
- optimization
- numerical linear algebra/eigenproblems
- FFT
- Monte Carlo
- parameter sweeps
- sensitivity/uncertainty
- numerical PDEs
- residuals, conditioning, convergence
- controlled approximations and asymptotics

### Stage 4 — Geometry, Tensors, Relativity
- tensor algebra
- coordinate transformations
- differential geometry/forms
- covariant derivatives
- curvature
- special/general relativity
- Einstein equations and conservation

### Stage 5 — Thermodynamics and Statistical Physics
- state variables/equations of state
- laws of thermodynamics
- entropy/free energies
- ensembles
- partition functions
- distributions, expectations, fluctuations

### Stage 6 — Quantum Mechanics
- complex/Hilbert spaces
- operators/eigenstates
- commutators/expectation values
- Schrödinger equation
- standard quantum systems
- angular momentum/spin
- tensor products
- time evolution
- perturbation theory
- density matrices

### Stage 7 — Field Theory and Advanced Mathematical Physics
- field Euler-Lagrange equations
- interacting fields
- Noether currents
- classical gauge fields
- stress-energy
- advanced tensor calculus
- selected field theories

### Stage 8 — Cross-Domain Scientific Synthesis
- mathematics-to-physics derivation chains
- problem representation/method selection
- dimensional consistency
- assumption propagation
- competing solution routes
- counterexample search
- exact/numerical/formal evidence comparison
- long-chain provenance

### Stage 9 — Formal Mathematics and Proof Escalation
- faithful Automate-to-Lean translation
- arithmetic/algebra/inequality proof
- selected calculus and linear algebra
- selected mechanics/tensor identities
- proof provenance
- explicit distinction between symbolic verification and formal proof

Formal evidence may be added earlier whenever a faithful boundary exists.

### Stage 10 — Research-Grade Scientific Reasoning
- problem decomposition
- representation and method selection
- hypothesis formation
- symbolic derivation
- numerical experiment design
- counterexample search
- assumption discovery
- competing-derivation analysis
- uncertainty/evidence assessment
- reproducible research provenance
- human review for genuinely ambiguous mathematics

## 8. Immediate capability queue

### 1B.1 Partial derivatives
Status: [~] being implemented on PR #211.

Required evidence:
- explicit differentiation variable
- multivariable semantics
- symbolic verification
- incorrect-variable rejection
- malformed/unsafe input rejection
- AI contract exposure
- regression evidence

### 1B.2 Total differentials
Status: [~] being implemented with 1B.1.

Required evidence:
- explicit variable list
- explicit differential symbols
- construction from partial derivatives
- residual/equality verification
- malformed-input rejection
- AI contract exposure
- regression evidence

### 1B.3 Higher-order partials
Not started.

### 1B.4 Jacobians
Not started.

### 1B.5 Hessians
Not started.

### 1B.6 Multivariable chain rule
Not started.

### 1B.7 Multivariable Taylor
Not started.

### 1B.8 Domain/assumption propagation
Not started as a general cross-cutting layer.

### 1B.9 Optimization
Not started as a complete verified family.

### 1C ODE
Existing ODE work is preserved but remains out of sequence until the active 1B frontier is satisfied.

## 9. Evidence workflow

For each capability:
1. inspect current implementation
2. inspect existing tests and contracts
3. identify the smallest reusable missing abstraction
4. implement it
5. test positive cases
6. test false claims
7. test malformed/unsupported/ambiguous cases
8. cross-check independently where practical
9. expose the machine contract
10. run focused regression
11. open/reconcile a coherent PR
12. merge only after review/evidence
13. run exact-head verification on the merged main SHA
14. run Security Audit
15. only then mark [x]

Never report a branch's green CI as certification of main.

## 10. AI compatibility

The preferred interaction is:

structured request
→ semantic validation
→ assumptions/domain resolution
→ backend selection
→ calculation
→ verification
→ cross-check
→ provenance/evidence
→ structured result

AI-generated expected values are untrusted.

An AI-facing request that cannot be semantically established must return an explicit failure state rather than a plausible answer.

## 11. Scientific test policy

Every capability family must accumulate:
- representative textbook cases
- nontrivial cases
- edge cases
- degenerate cases
- deliberately incorrect claims
- malformed requests
- unsupported semantics
- backend disagreement cases where feasible

Tests must verify semantics, not merely that a backend returned an expression.

## 12. Documentation policy

Do not maintain duplicate phase plans.

Update this ledger when:
- a capability changes certification state
- dependency order changes
- a new scientific capability is added to the authoritative queue
- evidence reveals a previous status was wrong
- architecture materially changes

Keep `docs/CAPABILITY_INVENTORY.json` as an implementation/evidence index.

Keep `docs/correct-10-stage-machinery-map-20261008` as historical/reference material only; it is not an operational authority.

## 13. Obsolete material

The following old planning documents are retired from operational use:
- `docs/PROJECT_PHASE_LEDGER.md`
- `docs/MATH_PHYSICS_ROADMAP.md`

They must not be consulted for sequencing after this ledger is merged.

The retirement is intentional: maintaining two competing roadmaps is how software projects acquire archaeology instead of architecture.

## 14. Operating rule for future agents

Read this file first.

Then inspect actual code, tests, and exact current main.

Do not ask the user to choose between obvious engineering actions.

Do not broaden scope into autonomous development control.

Do not declare capability completion without evidence.

Do not move to a later scientific domain merely because it is more interesting.

Build reusable mathematics first, then compose it into physics.

## 15. Current certification ledger

At establishment of this ledger:
- Stage 1A: previously certified capabilities remain certified only where current main evidence supports them.
- Stage 1B: active.
- Stage 1C: preserved, not current frontier.
- Stages 2–10: preserved capability inventory, not automatically certified as complete.
- PR #211: pending CI/security/reconciliation; not certified.
- Main: `e966cc286565c18356aca9a8d2f367c2db901fca`.

This ledger itself becomes authoritative only when merged to main and its exact-head verification/security gates pass.
