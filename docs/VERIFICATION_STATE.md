# Automate Verification State

## Current working state

**Current head at last audit:** `d413df09ec4eb22009da219c720a4b61bccb6ba4`

| State | Status |
|---|---|
| Implementation | **COMPLETE** |
| Architectural boundary | **COMPLETE** |
| Test coverage | **IMPLEMENTED** |
| CI | **VERIFIED for current head** |
| Merge to `main` | **NOT PERFORMED** |

The current head is the exact implementation checkpoint validated by GitHub Actions run #333. A verification claim is always bound to the exact commit SHA, not merely to the branch.


**Audit date:** 2026-10-04
**Repository:** `rynahmed101-sys/automate`
**Intended branch:** `feat/verification-hardening`
**Last fully CI-verified implementation commit:** `d413df09ec4eb22009da219c720a4b61bccb6ba4`
**CI:** GitHub Actions run #333 passed on that exact implementation commit.
**Published integration lineage:** `349b258` → recovery merge `ad702127` → upstream hardening `3e2fa552`
**Integration:** The feature branch contains the recovered local work plus the upstream hardening. No merge to `main` and no history rewrite occurred.

## Validation evidence

| Checkpoint | Result |
|---|---|
| GitHub Actions run #95, exact SHA `7070c6b1` | **PASS** |
| GitHub Actions run #26, exact SHA `9902a82c` | PASS |
| Python 3.10 full suite | PASS |
| Python 3.11 full suite | PASS |
| Python 3.12 full suite | PASS |
| Python 3.13 full suite | PASS |
| Explicit adversarial suite on Python 3.10–3.13 | PASS |
| Lean 4.34.1 backend proof-check job | PASS |
| Earlier exact-SHA run #19, `99ed4e1` | PASS |
| Earlier exact-SHA run #17, `58b098e` | PASS |

GitHub Actions [run #95](https://github.com/rynahmed101-sys/automate/actions/runs/37182226286) is the last completed exact-SHA verification for `7070c6b1`. All five jobs completed successfully: Python 3.10, 3.11, 3.12, Python 3.13, and the Lean 4.34.1 proof-check job. The verified tip includes the external-engine provenance hardening, canonical Tensor IR contract, EinsteinPy independent-engine classification, sandbox-limit tests, and the public-repository security workflow.

The earlier local Windows evidence remains separately classified and is not substituted for authoritative GitHub Actions evidence.

## Hardening completed in this phase

**SafeParser security boundary.** Untrusted mathematical text is now parsed into a restricted Python AST and translated through an explicit allowlist into SymPy objects. Source strings are not passed to `sympify`/Python evaluation. Attribute access, subscripting, arbitrary callables, keyword arguments, statement-like syntax and other non-mathematical constructs are rejected. AST size/depth and resulting expression size/depth are bounded.

**Shared execution sandbox.** The verification kernel now provides a reusable `VerifiedExecutionSandbox` with spawned-process isolation, hard parent-side wall-clock termination, bounded serialized input/output, best-effort POSIX CPU-time and address-space limits, constrained scientific-library thread counts, and explicit evaluation budgets. Numerical ODE and statistical fitting backends currently execute their expensive semantic work through this shared boundary. SafeParser retains its specialized isolated-parser boundary because its AST/result constraints are narrower and already independently hardened. Cross-engine adapters and future Cadabra workers should migrate onto the same sandbox contract rather than inventing separate resource controls.

**Dimensional semantics.** Unknown base dimensions and unknown coordinate-dimension descriptors now fail closed instead of silently becoming dimensionless. This prevents an unrecognized unit declaration from being treated as a successful dimensionless case.

**Symbolic division and assumption entailment.** `divide_both_sides` now delegates nonzero obligations to a centralized `AssumptionEntailment` layer. Active relational assumptions may jointly establish a consequence such as a product or positive sum; malformed, inactive, unsupported, or inconclusive assumptions never count as proof.

**Process-level parser isolation.** `SafeParser.parse_isolated` and `parse_equation_isolated` execute untrusted parsing in a spawned worker process with a hard parent-side wall-clock timeout and termination path. The worker now has a bounded serialized-result size. On POSIX platforms it also applies best-effort CPU-time and address-space limits; unsupported platform resource controls are not claimed as portable guarantees. Worker crashes are converted into controlled parser failures. The AI proposal validator uses this boundary for proposed output expressions before semantic verification.

**Capability honesty.** Lean capabilities in the rule registry now match the actual Lean backend scope. Only `conserve_energy`, `euler_lagrange`, and `algebraic_identity` are currently advertised as Lean-supported; arbitrary symbolic algebra rules are not falsely exposed as formally proved.

**Tensor claim binding.** Tensor verification now rejects a parameter-supplied named metric that conflicts with the graph input node, preventing the backend from silently verifying a different metric than the graph claims.

**Lean graph-claim binding.** The current canned Lean theorem families are now guarded by exact canonical graph-shape matching. Claims outside those canonical forms return `NOT_APPLICABLE` instead of being fed to a disconnected theorem template. This remains a conservative bridge, not a general graph-to-Lean translator.

**Dependency portability.** The tracked `requirements.txt` no longer contains machine-local Windows paths or a local wheel URL; it is environment-independent and aligned with the package dependency floor.

**Transactional proposal flow.** AI proposals continue to be validated, cloned, checked, and committed only after successful verification. Failed proposals leave the canonical graph unchanged.

**Numerical convergence evidence.** Numerical ODE checks now require successful integration plus stability under a deliberate tolerance-refinement probe. Reports record fine/coarse solver success, tolerances, absolute and normalized trajectory-difference estimates, function-evaluation counts and their ratio, trajectory fingerprints, and a SHA-256 fingerprint of the exact graph claim/configuration. This remains empirical convergence evidence, not a rigorous global error bound.

**Statistical provenance and independence.** Empirical inference now requires explicit data arrays, a caller-declared `data_source='observed'`, and a non-empty dataset ID. The byte-level dataset payload and graph/model claim are fingerprinted. `STATISTICALLY_CHECKED` now requires positive observational uncertainty; goodness-of-fit uses a configurable chi-square compatibility interval instead of hard-coded reduced-(chi^2) and R² acceptance thresholds. Local parameter identifiability is checked from a symbolic parameter Jacobian before certification. Confidence intervals use a Student-t critical value based on residual degrees of freedom. The provenance label remains caller-declared, not independently authenticated.

**Restricted graph-to-Lean translation.** `algebraic_identity` now has a real restricted translator for integer polynomial expressions: graph expressions are parsed, translated into Lean `Int` propositions, and compiled by the Lean CI job. Generated Lean evidence also records a graph-claim fingerprint binding the normalized graph expressions to the generated source; canonical mechanics obligations record their generated theorem proposition explicitly. Unsupported equation forms, non-integer coefficients, and broader symbolic/function constructs remain `NOT_APPLICABLE`.

**Tensor evidence provenance.** Tensor verification now records a SHA-256 fingerprint of the exact graph metric/claim/configuration, exact comparison method, coordinate/metric representation, and external-engine metadata. EinsteinPy unavailability is classified as `NOT_RUN`; an external-engine calculation failure is classified as `DISCREPANCY_DETECTED` rather than falsely reported as independent agreement. Successful EinsteinPy comparison remains `DIFFERENT_ENGINE` evidence rather than proof.

**Permanent mutation matrix.** The verification kernel now carries a deterministic adversarial mutation suite covering coefficient, sign, variable, dimension, domain, node kind, transformation rule, semantic parameters, side conditions, assumption predicates and assumption activation. The suite also mutates transitive upstream dependencies and unrelated graph state. Semantic mutations must change claim identity and stale the certificate; upstream-only mutations must leave claim identity stable while changing dependency identity; unrelated mutations must leave the certificate current. Evidence payload mutations are tracked independently from mathematical claim identity.

**Assumption dependency graph.** Assumptions now support explicit prerequisite relationships with cycle detection and transitive closure. Node inheritance includes those prerequisite assumptions, certificate identity therefore includes them, and assumption dependency changes can invalidate prior certificates. Dependency structure is serialized in the certificate package. Undeclared external assumptions remain explicit leaf premises rather than being silently invented.

**Structured tensor/index semantics.** The canonical tensor IR now represents tensor expressions and equations as structured index terms. Validation enforces rank/position consistency, Einstein dummy-index pairing, rejection of triple repeats, contracted-index dimension compatibility, and matching free-index signatures across sums and equations. TensorChecker consumes optional structured index data before component verification; malformed index structure fails closed.

**Graph-to-Lean translation.** The Lean backend now uses a generic graph-bound translator for algebraic claims rather than selecting a canned theorem from the rule name. The translator preserves the actual graph expressions, supports a bounded integer arithmetic/relation subset, rejects unsupported constructs explicitly, and can carry translatable inherited assumption predicates as explicit Lean hypotheses. Unsupported external assumptions remain provenance metadata rather than invented formal axioms. Broader calculus, tensor, and physics-law translation remains unsupported until those semantics can be represented faithfully.
## Phase 4.2: Cadabra integration

A bounded Cadabra2 external-engine adapter is now implemented at
`automate/tensors/cadabra_adapter.py`. Cadabra remains strictly external:
Automate does not vendor or import Cadabra source/runtime. The adapter detects
the CLI, records its version, fingerprints the exact source input, rejects the
initial unsupported external-control constructs, and executes the CLI through
`VerifiedExecutionSandbox`.

The initial supported boundary is deliberately narrow: explicitly supplied
Cadabra source plus an optional exact expected-output comparison. Successful
execution without an independent comparison target is recorded as
`COMPLETED` with independence class `UNVERIFIED`. A matching comparison is
`DIFFERENT_ENGINE` evidence; a mismatch is
`MATHEMATICAL_DISCREPANCY` / `CROSS_CHECK_FAILED`; unavailable Cadabra is
`UNAVAILABLE` / `NOT_RUN`; and sandbox/process failures are
`EXECUTION_FAILED` / `CROSS_CHECK_FAILED`. None of these paths treats
engine availability or execution success as proof.

A shared `ExternalEngineEvidence` provenance model is now available in
`automate/core/external_engine.py` for Cadabra and future external adapters.
The adapter records engine/version, input and output fingerprints, comparison
method, sandbox target/limits, execution status, and independence classification.

Run #178 validated Python 3.10, 3.11, 3.12, Python 3.13, and Lean 4.34.1; the full suites and explicit adversarial/mutation suite passed.\n\nThis milestone is an integration/provenance boundary; the graph-to-Cadabra bridge is now implemented for the strict structured Tensor AST subset described below. The canonical tensor IR remains the source of truth, and no
parallel tensor representation was introduced.

## Phase 4.3: canonical Tensor IR -> Cadabra translation

The external Cadabra boundary now has a semantic translation layer at
`automate/tensors/cadabra_translation.py`. It accepts structured
`TensorExpression.products` data, validates Einstein index structure before
translation, preserves tensor-factor names and index variance, and emits a
deterministic Cadabra expression plus a SHA-256 fingerprint of the canonical
IR input.

Legacy index-only `TensorExpression` values are deliberately rejected by the
translator because they do not retain tensor-factor identity. No tensor
symmetries, index spaces, or Cadabra properties are guessed from incomplete
IR metadata. The generated source is therefore a conservative expression
boundary, not a claim that every domain-specific Cadabra semantic property
has been reconstructed.


## Phase 4.3 completion: graph-bound Cadabra verification boundary

The canonical tensor path is now connected to graph AST data through
`automate/tensors/graph_translation.py`. Only explicit tensor/symbol nodes
and addition/multiplication are accepted. Raw expression strings are never
implicitly parsed, unsupported operations fail closed, tensor-factor identity
and index variance are preserved, and tensor physical dimensions are not
mistaken for index cardinalities.

The end-to-end API in `automate/tensors/cadabra_verification.py` now performs:

`graph AST -> canonical Tensor IR -> deterministic Cadabra translation -> IR SHA-256 -> bounded Cadabra execution -> provenance-bound evidence`

The verification path does not accept caller-supplied stdout as its comparison
target. It generates an independent structural rendering from the canonical
Tensor IR and compares that result with Cadabra's `str(ex)` output. This is
explicitly classified as **structural round-trip agreement**, not a general
symbolic proof. Tensor symmetries and index-space semantics are still not
invented when the graph IR does not provide them.

Cadabra source generation uses the documented `:=` assignment form, and the
external adapter now preserves the canonical IR fingerprint across unavailable,
execution-failure, unverified, discrepancy, and independent-agreement evidence
paths. Malformed fingerprints are rejected as non-hexadecimal SHA-256 values.

## Machine-agent interoperability hardening

The CLI schema discovery surface now accepts `ir`, `proposal`, and `context` explicitly. `automate schema --name proposal` and `automate schema --name context` emit JSON Schema directly from the authoritative Pydantic contract models, while `ir` emits the committed canonical graph schema. Unsupported schema names fail closed. These interfaces are covered by dedicated CLI contract tests.

The currently committed graph JSON schema is `automate.ir.v0.1`. The structured Tensor IR implementation has richer internal semantics, but a separately versioned Tensor IR JSON Schema remains future work and must not be advertised as an existing file until published.

## Current hardening additions

External-engine evidence now carries a provenance schema version, adapter version, resolved executable identity where available, and an executable SHA-256 fingerprint for Cadabra. External evidence fingerprints are themselves validated as hexadecimal SHA-256 values.

EinsteinPy is pinned to version 0.4.0 in project dependency metadata. EinsteinPy calculation failures are classified as `CROSS_CHECK_FAILED`, never as mathematical discrepancies. Supported EinsteinPy comparisons remain independently computed engine agreement, not formal proof.

The canonical Tensor IR now has a versioned machine-readable contract at `schemas/automate-tensor-v1.json`, and `automate schema --name tensor --json` exposes the authoritative Pydantic schema through the CLI contract surface.

A public-repository security workflow now runs CodeQL for Python and `pip-audit` against installed dependencies. Security Audit run #16 passed for the previous verified hardening tip; the final documentation-only synchronization commit requires its own exact-head CI run.

## Current capability assessment

| Capability | Current status |
|---|---|
| AI proposal validation / transaction integrity | PARTIALLY SUPPORTED, with fail-closed capability checks and clone-before-commit |
| Safe expression parsing | PARTIALLY SUPPORTED; structural parsing, wall-clock isolation, output-size bounds, and POSIX best-effort CPU/address-space limits are implemented; portability of OS resource controls remains limited |
| Algebra / ODE substitution | PARTIALLY SUPPORTED for implemented rule shapes; broad structured ODE coverage remains unverified |
| Euler-Lagrange mechanics | PARTIALLY SUPPORTED for implemented/tested systems; same-engine SymPy cross-checks are not independent engines |
| Tensor geometry | PARTIALLY SUPPORTED; TensorChecker is integrated for supported claims, with EinsteinPy cross-checks where available |
| Full 4D Schwarzschild | PARTIALLY SUPPORTED; selected components/properties are tested, not every requested property |
| Dimensions / assumptions | PARTIALLY SUPPORTED; missing versus explicit dimension metadata fails closed where applicable, and local relational entailment exists, but a full assumption theorem engine is incomplete |
| Numerics | PARTIALLY SUPPORTED; empirical tolerance-refinement evidence is recorded, but rigorous global error bounds and numerical process-level resource quotas remain incomplete |
| Statistics | PARTIALLY SUPPORTED; graph/model binding, dataset provenance/fingerprints, symbolic identifiability, uncertainty-aware goodness-of-fit, and residual diagnostics are recorded, but provenance is caller-declared rather than authenticated and statistical model assumptions are not fully automatic |
| Field variation / generalized mechanics | PARTIALLY SUPPORTED |
| Mathlib / Physlib graph-bound formalization | PARTIALLY SUPPORTED; restricted integer-polynomial algebraic identities are translated from graph expressions into Lean with claim-bound evidence, while broader mechanics/formal-library proposition binding remains unsupported |

## Evidence and circularity classification

- **Same-engine consistency:** internal TensorGeometry identities and single-path SymPy checks are regression evidence, not independent verification.
- **Same engine, distinct path:** Automate Euler-Lagrange derivation versus `sympy.calculus.euler` is useful cross-checking but remains within SymPy.
- **Cross-engine:** selected tensor results are compared with EinsteinPy. Agreement is evidence, not proof.
- **Externally known results:** selected polar, sphere and Schwarzschild components are checked against analytic/textbook values recorded in tests.
- **Numerical evidence:** solver output plus tolerance refinement supports empirical numerical stability only; it does not establish model correctness or a rigorous global error bound.
- **Statistical evidence:** fit quality does not establish physical truth; dataset provenance is explicit but caller-declared and not independently authenticated.
- **Formal proof:** Lean CI proves the repository's submitted Lean propositions. The algebraic-identity subset is now generated from the actual graph expressions; canonical mechanics theorems remain separately guarded and are not a general translator.

## Ecosystem notes

SymPy 1.14 documentation explicitly warns that `sympify()` uses `eval` and should not be used on unsanitized input. Automate's structural parser is therefore intentionally stricter than direct SymPy string parsing. citeturn457216search0turn457216search1

Mathlib4 remains actively maintained, with `v4.34.1` listed as the latest stable release at audit time and `v4.35.0-rc3` as a prerelease. Physlib is an active Lean project for digitalising physics results. These libraries are candidates for reuse only where their formal proposition genuinely matches an Automate graph claim. citeturn546223search0turn546223search8

EinsteinPy remains the intended cross-engine reference for supported symbolic differential-geometry checks. Its documentation demonstrates symbolic metric, curvature and Weyl-tensor calculations, but version/licensing details must be pinned in project metadata before being used as certificate evidence. citeturn457216search24

## Open-world claim handling

Automate treats verification as an evidence discipline, not a requirement that every proposed claim reduce to an established law. A hypothesis can enter the derivation graph as a hypothesis or exploratory claim without matching a canonical theorem family. The verification kernel records the exact claim identity, its dependency state, and any evidence produced by a backend. Unsupported claims remain unverified rather than being silently rejected as false; established laws are available as reusable verification targets, not as the boundary of what the system is allowed to investigate.

The canonical claim identity deliberately excludes backend-specific tolerances, execution controls, sampled observations, and machine details. Those belong to evidence provenance. This separation allows different backends to examine the same mathematical claim and allows genuinely new claims to accumulate reproducible evidence without pretending that the current knowledge base is complete.

## Completed roadmap

The previously tracked verification-hardening, Phase 4.2/4.3 Cadabra integration, canonical Tensor IR, independent semantic comparison, runtime provenance, CI/security verification, and dependency-maintenance milestones are **COMPLETED**.

The authoritative current integration head is `72efcbb67bbaf09d9fa1e26cd3e2d93da41a0599`. GitHub Actions Automate CI and Security Audit both pass on that exact `main` head.

The GitHub workspace/private-repository activation request was administrative rather than an engineering dependency and has been closed as superseded. The repository currently remains public only for this engineering window; the single developer will change visibility to private from GitHub administrator settings after this checkpoint.

## Next development upgrades

These are intentionally future development items, not claims of incomplete baseline verification:

1. **Broader independent tensor coverage.** Expand EinsteinPy/textbook cross-checks for tensor identities, contractions, curvature components, and supported index operations where the canonical IR carries sufficient semantics. Unsupported semantics must remain `UNSUPPORTED_SEMANTICS` or `UNVERIFIED`.
2. **Semantic Cadabra comparison.** Extend the current structural round-trip check toward independently computed semantic comparison only where index spaces, variance, metric data, and symmetries are explicitly represented. Never infer missing semantics.
3. **Structured mathematics coverage.** Expand ODEs, mechanics, field variation, and numerical certificates in small, testable rule families with explicit contracts rather than a generic “solve anything” interface.
4. **Stronger numerical evidence.** Add more reproducible error/convergence certificates, deterministic solver configurations, and host-aware resource quotas while keeping empirical convergence distinct from rigorous mathematical error bounds.
5. **Authenticated statistical provenance.** Move beyond caller-declared dataset labels toward resolvable dataset lineage, immutable source identifiers, and stronger model-assumption provenance where the execution environment permits it.
6. **Graph-bound formal verification.** Generalize Lean translation beyond the current integer-polynomial subset and reuse mathlib/physlib results only when proposition identity is mechanically preserved.
7. **Versioned external-engine registry.** Consolidate engine version, executable identity, license, input/output fingerprints, comparison method, sandbox limits, and independence classification into a reusable registry/certificate contract for future adapters.
8. **Machine-agent contract surface.** Publish and test a versioned Tensor IR JSON contract, capability discovery, deterministic schema negotiation, and stable CLI/API behavior so external AI agents can use Automate without relying on internal Python implementation details.
9. **Certificate lifecycle and reproducibility.** Add explicit certificate schema/version migration, evidence invalidation/reverification workflows, and deterministic export/import checks without conflating provenance with proof.
10. **Single-developer maintenance discipline.** Prefer consolidated changes and squash merges, avoid unnecessary repository/workspace machinery, and require exact-head CI/security verification before declaring an engineering milestone complete.

Claims not supported by source inspection or an executed check remain **UNVERIFIED**.
