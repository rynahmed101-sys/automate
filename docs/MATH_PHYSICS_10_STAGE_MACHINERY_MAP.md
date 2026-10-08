# Automate 10-Stage Mathematical-Physics Machinery Map

**Status:** authoritative machinery map for the ten-stage mathematical/physics ledger  
**Scope:** only the reusable machinery represented by `docs/PROJECT_PHASE_LEDGER.md`. This document does **not** inventory every mathematical or physics capability already present in the repository.  
**Branch prepared:** `docs/correct-10-stage-machinery-map-20261008`

## Purpose

The project phase ledger describes the scientific capability ladder. It does not, by itself, distinguish between:

- machinery actually integrated into the authoritative Automate path;
- machinery that exists in preserved later-stage work but is intentionally out of order;
- machinery that exists but is currently broken;
- machinery that is only partially implemented;
- machinery that does not exist.

This map makes that distinction explicit.

The map is intentionally stricter than a normal capability inventory. **Code existing somewhere is not equivalent to working machinery owned by Automate's current authoritative path.**

## Status symbols

- **✓ Fully integrated** — machinery is on the authoritative Automate path and the relevant verified slice has passed the project's evidence boundary. This does not mean the entire scientific family is complete.
- **◇ Present, but out of order** — real implementation exists in preserved branches, historical integration packets, or later-stage code, but it is not part of the authoritative active path and must not be counted as current integrated capability.
- **◐ Partially missing** — a meaningful portion of the machinery exists or its foundation exists, but important general pieces required by the ledger are absent.
- **⚠ Present but broken** — implementation is intended to serve the machinery but is known to be non-working, inconsistent, stale, or otherwise unusable in its present form.
- **○ Completely missing** — no authoritative implementation of the required machinery was found.

### Critical rule

A stage may contain entries in several categories. A stage is **not complete** merely because it contains a ✓ entry. Stage completion still follows the authoritative ledger and its exit condition.

---

# Stage 1 — Complete Core Mathematical Engine

## ✓ Fully integrated

- Core linear-algebra representation and operations: vectors, matrices, subspaces, bases, transformations, complex/Hermitian semantics, norms and inner products.
- Verified linear-algebra extensions already accepted into main, including quadratic forms, SVD, pseudoinverse and least-squares machinery.
- Core calculus infrastructure that is already represented on the authoritative path, including the fundamental-theorem boundary, improper-integral/convergence handling, and Taylor/Maclaurin expansion machinery where already verified.
- Canonical mathematical IR/rules/schema boundaries used by these capabilities.

## ◇ Present, but out of order

- Reusable ODE foundation: separable/linear and broader ODE machinery, represented by preserved Stage 1C work. It must not be treated as current Stage 1 completion because the remaining 1B frontier precedes it.
- Later ODE integration/test assets preserved for future reconciliation.

## ◐ Partially missing

- General limits and continuity.
- General derivatives and higher-order derivatives without artificial ceilings.
- General integration coverage beyond the already implemented slices.
- Partial derivatives and total differentials.
- Higher-order partial derivatives.
- Jacobians and Hessians.
- Multivariable chain rule.
- Stationary points and constrained optimization.
- Domain/singularity/assumption-aware calculus.
- General ODE representation and verification on the authoritative path.

## ⚠ Present but broken

- No scientific Stage-1 family is classified ⚠ merely because an old branch or stale packet needs repair. Broken means the authoritative implementation itself is known to be non-working. The current evidence does not justify marking the scientific Stage-1 machinery that way.

## ○ Completely missing

- No completely separate Stage-1 mathematical foundation is required beyond the above; the remaining gaps are primarily ◐ partial rather than total absence.

**Stage verdict:** **◐ Incomplete, with a strong ✓ foundation and ◇ later work.** Stage 1 is not complete.

---

# Stage 2 — Core Mathematical Physics

## ✓ Fully integrated

- Vector-calculus core: scalar/vector fields, gradient, directional derivative, divergence, curl, Laplacian, line/surface/volume integrals and the implemented Green/Stokes/divergence-theorem slices.
- Verified classical-mechanics slices already merged, including constraints/Lagrange multipliers, Lagrangian mechanics and Hamilton equations.
- Verified electromagnetism slices already merged, including the implemented electrostatic foundations, differential Maxwell equations, Lorentz force and Poynting-vector/energy-balance work.

## ◇ Present, but out of order

- Coordinate-aware vector-calculus and generic PDE-residual foundation preserved from the Stage 2B work.
- Fourier/Laplace transform and convolution foundation preserved from later integration work.
- Statistical/waves/optics work preserved from later-stage branches.
- Additional mechanics/electromagnetism work preserved outside the currently authoritative staged path.

## ◐ Partially missing

- General coordinate-aware field operations and broader conservative-field/potential reconstruction.
- PDE representation, residual verification and fail-closed PDE semantics.
- PDE domain, singularity and assumption propagation.
- Initial/boundary-condition representation and compatibility checking.
- Separation-of-variables machinery.
- Green-function machinery.
- Fourier-series representation, coefficient computation, reconstruction and convergence handling.
- Fourier-transform and inverse-transform semantics.
- Continuous convolution and convolution-theorem machinery.
- Laplace-transform and inverse-transform semantics.
- Transform/PDE composition and acceptance campaigns.
- Broader classical mechanics: kinematics/dynamics, Poisson brackets, canonical transformations, central-force problems, coupled oscillators, rigid bodies and rotating frames.
- Broader electromagnetism: magnetic laws/fields, potentials, gauge conditions, integral Maxwell equations, differential/integral consistency, charge conservation, electromagnetic wave equation.
- Waves and optics as a reusable domain.

## ⚠ Present but broken

- No Stage-2 scientific implementation is marked ⚠ without direct evidence that the authoritative code itself is broken. Preserved branches with stale shared-file edits are not treated as authoritative broken main machinery; they remain ◇ until reconciled.

## ○ Completely missing

- No entire Stage-2 domain can honestly be called completely absent because substantial vector-calculus, mechanics and electromagnetism machinery exists. The missing material is distributed partial machinery rather than an empty stage.

**Stage verdict:** **◐ Substantially started, but far from complete.** The most important distinction is that PDE/transforms are ◇/◐, not integrated merely because historical implementations exist.

---

# Stage 3 — Numerical, Approximate & Scientific Reasoning

## ✓ Fully integrated

- Numerical/evidence infrastructure that supports verification and cross-checking is integrated into the broader Automate architecture.
- Mathematical evidence/provenance machinery can represent verification results and failure states.

## ◇ Present, but out of order

- Numerical mathematics foundation preserved in later-stage implementation work, including numerical core machinery.
- Statistical backend and associated scientific-statistical work preserved for later reconciliation.
- Numerical algorithms and scientific-evidence components that were developed ahead of the dependency order but are not yet the authoritative Stage-3 path.

## ◐ Partially missing

- General numerical root finding and nonlinear systems.
- Numerical differentiation and quadrature as a unified scientific subsystem.
- Interpolation and optimization.
- Numerical linear algebra/eigenproblems as a unified reusable layer.
- FFT and Monte Carlo machinery.
- Parameter sweeps and sensitivity analysis.
- Uncertainty propagation.
- Numerical PDE methods.
- Conditioning and convergence evidence.
- Controlled approximation as a first-class semantic layer.
- Small-parameter/asymptotic/perturbative reasoning.
- Distinction and composition of exact, approximate and numerical claims.
- Error/residual tracking attached to derivations.
- Independent computational-route comparison.

## ⚠ Present but broken

- No specific Stage-3 scientific subsystem is classified ⚠ on current evidence. Some preserved implementations are incomplete or require reconciliation, which is represented as ◇ rather than pretending they are broken main machinery.

## ○ Completely missing

- A unified approximation/evidence model that makes approximation order, validity region, error and assumptions first-class is effectively absent from the authoritative path.

**Stage verdict:** **◐/◇.** Useful numerical/evidence foundations exist, but the actual Stage-3 scientific reasoning layer is not yet integrated as a complete subsystem.

---

# Stage 4 — Geometry, Tensors & Relativity

## ✓ Fully integrated

- Tensor representations and tensor-algebra infrastructure already used by Automate.
- Tensor backend/adaptor foundations and semantic comparison infrastructure where already integrated and verified.
- Existing formal/tensor translation boundaries that support later escalation.

## ◇ Present, but out of order

- Higher tensor-calculus work and geometry-related implementations preserved in later-stage development.
- Cadabra/EinsteinPy integration boundaries and tensor/geometry research machinery that are not yet the authoritative general geometry engine.
- Existing metric/dimension and formalization groundwork.

## ◐ Partially missing

- Arbitrary-rank tensor operations as a complete user-facing/general semantic family.
- Index raising/lowering and full index semantics.
- Symmetrization/antisymmetrization as a general geometric layer.
- Coordinate transformations.
- Covariant derivatives and metric compatibility.
- Lie derivatives.
- Differential forms, wedge products, exterior derivatives, pullbacks and Hodge dual.
- General curvature and geometric-invariant pipeline.
- General geodesic and conservation machinery.

## ○ Completely missing

- A complete general relativity reasoning subsystem: Einstein field equations, broad stress-energy handling, Killing-vector machinery, geodesic deviation, Schwarzschild/FLRW reusable spacetime models and their systematic verification are not present as an integrated Stage-4 engine.

## ⚠ Present but broken

- No authoritative Stage-4 scientific subsystem is classified ⚠ without direct current-main failure evidence.

**Stage verdict:** **◐ with ◇ groundwork.** Tensor infrastructure exists, but the geometry/relativity machinery described by the ledger is not integrated as a mature general system.

---

# Stage 5 — Thermodynamics & Statistical Physics

## ✓ Fully integrated

- General statistical/evidence infrastructure exists and can support later physical probability reasoning.

## ◇ Present, but out of order

- Statistical backend and related inference machinery developed ahead of the staged dependency order.

## ◐ Partially missing

- Physical-state representation.
- Equations of state.
- Thermodynamic process/state transitions.
- Entropy and thermodynamic potentials.
- Maxwell relations.
- Phase equilibrium.
- Microstate/macrostate representation.
- Ensemble semantics.
- Expectation/fluctuation machinery tied to physical ensembles.

## ○ Completely missing

- A unified thermodynamics engine covering first/second laws, entropy, state variables, potentials and equilibrium reasoning.
- A unified statistical-mechanics engine covering partition functions, canonical/grand-canonical ensembles and their physical composition.

## ⚠ Present but broken

- No current authoritative Stage-5 subsystem is marked broken on the evidence available.

**Stage verdict:** **○/◐.** General statistical plumbing exists, but the ledger's actual thermodynamic/statistical-physics machinery is largely missing or only preserved out of order.

---

# Stage 6 — Quantum Mechanics

## ✓ Fully integrated

- Mathematical prerequisites already integrated include complex scalar/vector/matrix semantics, Hermitian linear algebra and eigenvalue/eigenvector machinery.
- Tensor-product groundwork exists in the broader mathematical infrastructure where applicable.

## ◇ Present, but out of order

- ODE, numerical, approximation and formal-proof machinery that can become prerequisites for quantum mechanics.
- Selected quantum-adjacent mathematical work may exist in preserved branches, but it is not counted as an integrated QM engine without the required state/operator semantics.

## ◐ Partially missing

- General operator semantics beyond ordinary matrices.
- State representation tied to physical Hilbert spaces.
- Observable/measurement semantics.
- Expectation values and uncertainty as physical reasoning objects.
- Schrödinger evolution and stationary-state reasoning.
- Density matrices and mixed states.
- Physical tensor-product state composition.
- Quantum-specific verification/evidence semantics.

## ○ Completely missing

- A complete reusable quantum-mechanics reasoning engine.
- General Hilbert-space state machinery.
- A first-class measurement/probability model.
- Integrated quantum dynamics and state-evolution machinery.

## ⚠ Present but broken

- No authoritative QM subsystem is classified ⚠.

**Stage verdict:** **○/◐.** The linear-algebra substrate is real, but that substrate must not be misreported as quantum mechanics.

---

# Stage 7 — Field Theory & Advanced Mathematical Physics

## ✓ Fully integrated

- General variational/tensor/calculus prerequisites exist in Automate's broader codebase.

## ◇ Present, but out of order

- Scalar-field variational foundation and field-theory implementation work preserved from later-stage development.
- Field-theory directory and associated tests/work that are not yet authoritative Stage-7 completion.

## ◐ Partially missing

- Generalized field Euler-Lagrange machinery.
- Multiple interacting fields.
- Noether currents and symmetry/conservation linkage.
- Gauge-field abstraction.
- Action-to-field-equation derivation pipeline.
- General stress-energy derivation.
- Reusable field-theory representations.

## ○ Completely missing

- A mature general field-theory reasoning engine capable of systematically composing fields, actions, symmetries, equations of motion and conserved quantities.

## ⚠ Present but broken

- No direct evidence justifies marking the preserved field-theory implementation as broken. Its current state is more accurately ◇, because it is not authoritative/integrated.

**Stage verdict:** **◇/◐.** Real groundwork exists, but Stage 7 is not integrated.

---

# Stage 8 — Cross-Domain Synthesis

## ✓ Fully integrated

- Canonical mathematical IR and shared representations.
- Dimensions/units and assumptions as reusable semantic foundations where already implemented.
- Claim/graph/node/edge structures.
- Evidence/provenance structures.
- Cross-backend translation/comparison foundations.
- Machine-agent contracts and reusable verification boundaries.

## ◇ Present, but out of order

- Advanced cross-domain research and integration packets preserved from earlier work.
- Later-stage reasoning components that have been developed before the scientific prerequisite ladder was complete.

## ◐ Partially missing

- Automatic mathematics-to-physics derivation planning.
- Physics-to-required-mathematics selection.
- General method selection from problem structure.
- Cross-domain assumption propagation through long derivations.
- Multiple-route derivation comparison as a general planner.
- Counterexample generation driven by the structure of the claim.
- Insufficiency detection as a general scientific reasoning operation.
- Long-chain cross-domain provenance as a single durable object.
- A unified cross-domain conductor that chooses and composes the existing engines.

## ○ Completely missing

- No complete autonomous scientific cross-domain conductor exists. The infrastructure for one is substantial, but the actual mathematical-physics synthesis loop described by Stage 8 is not yet present as a mature integrated engine.

## ⚠ Present but broken

- No scientific Stage-8 subsystem is classified ⚠ without direct current-main evidence.

**Stage verdict:** **✓ substrate + ◐ reasoning layer.** The plumbing is much further along than the scientific conductor.

---

# Stage 9 — Formal Mathematics & Proof Escalation

## ✓ Fully integrated

- Lean/formal backend boundary.
- Translation machinery from selected Automate structures into formal representations.
- Formal-evidence distinction and proof-oriented test infrastructure.
- Existing tensor/formal translation foundations.

## ◇ Present, but out of order

- Formalization work attached to later-stage mathematical/physics capabilities.
- Selected proof experiments and capability-specific formal packets developed before the complete scientific ladder is mature.

## ◐ Partially missing

- Automatic decision logic for when a claim should escalate to formal proof.
- Durable correspondence tracking between Automate IR and generated proof objects.
- Broader automated formalization coverage for calculus, linear algebra, mechanics and tensor identities.
- Formal-proof provenance integrated across multi-step derivations.

## ○ Completely missing

- A broad general-purpose automatic formal-escalation conductor covering the Stage-9 target families end-to-end.

## ⚠ Present but broken

- No Stage-9 scientific machinery is classified ⚠ without direct current-main failure evidence.

**Stage verdict:** **✓ formal substrate + ◐ escalation.** Automate can already cross the formal boundary in selected cases, but it does not yet systematically decide and execute formal escalation across its scientific reasoning.

---

# Stage 10 — Research-Grade Mathematical-Physics Reasoning

## ✓ Fully integrated

- Research-request/evidence structures.
- AI provider/context and proposal machinery.
- Discovery and future-capability machinery.
- Learning artifacts, learning loop and learning runtime.
- Experiment/evidence structures.
- Counterexample-oriented verification and failure diagnosis.
- Autonomous control, worker execution, reconciliation, promotion, bookkeeping and readiness machinery.

These are real and integrated as **development/research infrastructure**.

## ◇ Present, but out of order

- Research and autonomous-worker components developed ahead of the scientific Stage-10 reasoning ladder.
- Mirror research/mission execution machinery and associated experimental infrastructure that is now being integrated into the triad but is not itself proof of scientific reasoning completeness.

## ◐ Partially missing

- Problem decomposition tied to mathematical structure.
- Representation selection from the actual problem.
- Method selection from available mathematical/physical machinery.
- Hypothesis formation constrained by evidence and assumptions.
- Automatic competing-derivation generation and comparison.
- Experiment design driven by uncertainty or unresolved premises.
- Assumption discovery from failed derivations.
- Unified evidence-quality reasoning across symbolic, numerical, formal and experimental sources.
- Complete research-grade provenance chain connecting question → representation → method → derivation → experiment → evidence → conclusion.

## ○ Completely missing

- A mature autonomous scientific reasoning conductor that can independently take a mathematical-physics research problem, choose representations and methods, construct competing solutions, design validation experiments, detect missing assumptions, compare evidence, and produce an auditable research conclusion.

## ⚠ Present but broken

- The development/autonomy control plane currently has known defects in the broader repository test surface. Those defects must be repaired before the control plane can honestly be treated as fully healthy. They are **not** evidence that the Stage-10 scientific reasoning engine itself exists and is broken.
- Therefore Stage-10 scientific machinery is not marked ⚠; its main problem is ◐ missing reasoning, not a broken finished implementation.

**Stage verdict:** **✓ autonomous development substrate + ◐ scientific reasoning.** This is the most important distinction in the entire map.

---

# Ten-stage reality in one view

| Stage | ✓ Integrated | ◇ Out of order | ◐ Partially missing | ⚠ Broken | ○ Completely missing |
|---|---|---|---|---|---|
| 1 | Strong linear algebra + verified calculus slices | ODE foundation | Most remaining calculus + authoritative ODE integration | None justified | No whole foundation absent |
| 2 | Vector calculus + selected mechanics/EM | PDE/transforms, stats/optics, later physics | Most PDE/transforms + broader mechanics/EM/optics | None justified | No whole stage absent |
| 3 | Evidence/numerical substrate | Numerical/statistical implementations | Unified numerical + approximation + scientific evidence | None justified | Unified approximation semantics |
| 4 | Tensor/formal substrate | Geometry adapters/work | General geometry/differential forms/relativity | None justified | Mature GR engine |
| 5 | Statistical substrate | Statistical backend | Physical thermodynamics/statistical composition | None justified | Unified thermo + stat-mech engines |
| 6 | Complex LA prerequisites | Adjacent prerequisites | QM semantics | None justified | Complete QM engine |
| 7 | Variational/tensor prerequisites | Scalar-field work | General field theory | None justified | Mature field-theory engine |
| 8 | Shared IR/evidence/graph substrate | Advanced integration packets | Scientific cross-domain conductor | None justified | Complete autonomous synthesis conductor |
| 9 | Lean/formal substrate | Capability-specific formal work | Escalation/correspondence/provenance | None justified | General formal-escalation conductor |
| 10 | Research/autonomy development substrate | Later research/mission machinery | Scientific reasoning conductor | Control-plane defects exist, but are separate from scientific Stage-10 machinery | Mature autonomous research-reasoning engine |

# What this changes

1. **Do not count preserved branches as integrated capabilities.** They are marked ◇.
2. **Do not count prerequisites as the domain itself.** Complex linear algebra is not quantum mechanics; tensor algebra is not general relativity; statistical infrastructure is not thermodynamics.
3. **Do not call a stage complete because one family inside it is verified.**
4. **Do not call preserved implementation broken unless current evidence demonstrates that the implementation itself is broken.** Stale/out-of-order work is ◇.
5. **Do not confuse the autonomy/control plane with scientific reasoning.** Automate is considerably more mature at managing development than at independently doing research-grade mathematical-physics reasoning.
6. **The earliest incomplete stage remains Stage 1.** Later-stage machinery may be harvested when its dependencies become appropriate, but it must not move the active frontier forward by declaration.
7. **The ten-stage map is now a machinery map, not a capability inventory.** Capability-level evidence can remain in `docs/CAPABILITY_INVENTORY.json`, but that file must not override this map's classification of integration/order.

# Authority

- **Roadmap/order authority:** `docs/PROJECT_PHASE_LEDGER.md`
- **Ten-stage machinery classification:** this document
- **Capability-level implementation/evidence companion:** `docs/CAPABILITY_INVENTORY.json`
- **System/autonomy architecture:** `docs/AUTONOMOUS_SYSTEM_MASTER_PLAN.md`
- **Compatibility roadmap pointer:** `docs/MATH_PHYSICS_ROADMAP.md` is obsolete as a roadmap and must not be used to determine stage status.

**Map baseline:** current authoritative Automate main at the time this map was prepared: `828e8b520f4ffb8341eea4e9de5d630bc2ef1f8c`.

**Verification rule:** this document is a classification of repository state, not an assertion that every ✓ entry is currently re-verified at the latest main SHA. Fresh Exact-head and Security evidence is required after subsequent main changes.
