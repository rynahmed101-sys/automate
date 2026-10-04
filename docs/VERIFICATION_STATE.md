# Automate Verification State

**Audit date:** 2026-10-04
**Repository:** `rynahmed101-sys/automate`
**Intended branch:** `feat/verification-hardening`
**Verified code commit:** `7070c6b1fab08501f5295ea455e246ce9fa8fd13`
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

GitHub Actions [run #95](https://github.com/rynahmed101-sys/automate/actions/runs/37182226286) is the current completed exact-SHA verification for `7070c6b1`. All five jobs completed successfully: Python 3.10, 3.11, 3.12, Python 3.13, and the Lean 4.34.1 proof-check job. The verified tip includes the statistical graph-claim binding and identifiability hardening, expanded numerical evidence, tensor cross-check provenance, Lean claim fingerprints, and SafeParser process/resource isolation changes.

The earlier local Windows evidence from the integrated recovery work remains separately classified: 235 passed / 1 skipped for the full suite and 30 passed / 1 skipped for the adversarial suite. The local Lean skip was caused by an unusable Lean shim/toolchain and is not evidence of local Lean proof execution.

## Hardening completed in this phase

**SafeParser security boundary.** Untrusted mathematical text is now parsed into a restricted Python AST and translated through an explicit allowlist into SymPy objects. Source strings are not passed to `sympify`/Python evaluation. Attribute access, subscripting, arbitrary callables, keyword arguments, statement-like syntax and other non-mathematical constructs are rejected. AST size/depth and resulting expression size/depth are bounded.

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

## Remaining work

1. Expand tensor claim binding and independent EinsteinPy/textbook coverage without marking unsupported whole-tensor or index-operation claims as verified.
2. Extend numerical process-level resource isolation with explicit CPU/memory bounds and document platform-specific limits; SafeParser now has best-effort POSIX CPU/address-space controls plus cross-platform wall-clock termination.
3. Generalize structured ODEs, mechanics, field variation, and numerical error certificates only where semantics are explicit and testable.
4. Expand statistical provenance beyond caller-declared labels to authenticated or externally resolved dataset lineage where the execution environment permits it, and formalize more of the statistical model assumptions.
5. Generalize graph-to-Lean translation beyond the restricted integer-polynomial subset; reuse mathlib/physlib theorems only when proposition identity is preserved.
6. Pin external-engine versions, licenses, inputs/results and independence metadata in `docs/ECOSYSTEM.md` and verification certificates.

Claims not supported by source inspection or an executed check remain **UNVERIFIED**.
