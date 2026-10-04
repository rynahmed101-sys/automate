# Automate Verification State

**Audit date:** 2026-10-04
**Repository:** `rynahmed101-sys/automate`
**Intended branch:** `feat/verification-hardening`
**Verified code commit:** `19904dc3ebd2e639176f47e687f35c64d94fa2a3`
**Published integration lineage:** `349b258` → recovery merge `ad702127` → upstream hardening `3e2fa552`
**Integration:** The feature branch contains the recovered local work plus the upstream hardening. No merge to `main` and no history rewrite occurred.

## Validation evidence

| Checkpoint | Result |
|---|---|
| GitHub Actions run #34, exact SHA `19904dc3` | **PASS** |
| GitHub Actions run #26, exact SHA `9902a82c` | PASS |
| Python 3.10 full suite | PASS |
| Python 3.11 full suite | PASS |
| Python 3.12 full suite | PASS |
| Python 3.13 full suite | PASS |
| Explicit adversarial suite on Python 3.10–3.13 | PASS |
| Lean 4.34.1 backend proof-check job | PASS |
| Earlier exact-SHA run #19, `99ed4e1` | PASS |
| Earlier exact-SHA run #17, `58b098e` | PASS |

GitHub Actions [run #34](https://github.com/rynahmed101-sys/automate/actions/runs/37179619813) is the current completed exact-SHA verification for `19904dc3`. All five jobs completed successfully, including Python 3.10–3.13 full suites, explicit adversarial tests, and the Lean 4.34.1 proof-check job.

The branch has since advanced beyond this checkpoint with isolated SafeParser execution, AI-boundary parsing, and conservative Lean graph-claim binding. Those newer commits remain pending exact-SHA CI verification at audit time.

The earlier local Windows evidence from the integrated recovery work remains separately classified: 235 passed / 1 skipped for the full suite and 30 passed / 1 skipped for the adversarial suite. The local Lean skip was caused by an unusable Lean shim/toolchain and is not evidence of local Lean proof execution.

## Hardening completed in this phase

**SafeParser security boundary.** Untrusted mathematical text is now parsed into a restricted Python AST and translated through an explicit allowlist into SymPy objects. Source strings are not passed to `sympify`/Python evaluation. Attribute access, subscripting, arbitrary callables, keyword arguments, statement-like syntax and other non-mathematical constructs are rejected. AST size/depth and resulting expression size/depth are bounded.

**Dimensional semantics.** Unknown base dimensions and unknown coordinate-dimension descriptors now fail closed instead of silently becoming dimensionless. This prevents an unrecognized unit declaration from being treated as a successful dimensionless case.

**Symbolic division and assumption entailment.** `divide_both_sides` now delegates nonzero obligations to a centralized `AssumptionEntailment` layer. Active relational assumptions may jointly establish a consequence such as a product or positive sum; malformed, inactive, unsupported, or inconclusive assumptions never count as proof.

**Process-level parser isolation.** `SafeParser.parse_isolated` and `parse_equation_isolated` execute untrusted parsing in a spawned worker process with a hard parent-side wall-clock timeout and termination path. The AI proposal validator now uses this boundary for proposed output expressions before semantic verification.

**Capability honesty.** Lean capabilities in the rule registry now match the actual Lean backend scope. Only `conserve_energy`, `euler_lagrange`, and `algebraic_identity` are currently advertised as Lean-supported; arbitrary symbolic algebra rules are not falsely exposed as formally proved.

**Tensor claim binding.** Tensor verification now rejects a parameter-supplied named metric that conflicts with the graph input node, preventing the backend from silently verifying a different metric than the graph claims.

**Lean graph-claim binding.** The current canned Lean theorem families are now guarded by exact canonical graph-shape matching. Claims outside those canonical forms return `NOT_APPLICABLE` instead of being fed to a disconnected theorem template. This remains a conservative bridge, not a general graph-to-Lean translator.

**Dependency portability.** The tracked `requirements.txt` no longer contains machine-local Windows paths or a local wheel URL; it is environment-independent and aligned with the package dependency floor.

**Transactional proposal flow.** AI proposals continue to be validated, cloned, checked, and committed only after successful verification. Failed proposals leave the canonical graph unchanged.

## Current capability assessment

| Capability | Current status |
|---|---|
| AI proposal validation / transaction integrity | PARTIALLY SUPPORTED, with fail-closed capability checks and clone-before-commit |
| Safe expression parsing | PARTIALLY SUPPORTED; structural parsing and killable isolated proposal-boundary parsing are implemented, but full runtime coverage and memory/resource quotas remain incomplete |
| Algebra / ODE substitution | PARTIALLY SUPPORTED for implemented rule shapes; broad structured ODE coverage remains unverified |
| Euler-Lagrange mechanics | PARTIALLY SUPPORTED for implemented/tested systems; same-engine SymPy cross-checks are not independent engines |
| Tensor geometry | PARTIALLY SUPPORTED; TensorChecker is integrated for supported claims, with EinsteinPy cross-checks where available |
| Full 4D Schwarzschild | PARTIALLY SUPPORTED; selected components/properties are tested, not every requested property |
| Dimensions / assumptions | PARTIALLY SUPPORTED; unknown dimensions fail closed and local relational entailment now exists, but missing-vs-explicit dimension metadata remains unresolved |
| Numerics | PARTIALLY SUPPORTED; numerical results are evidence, not proofs, and general error/convergence certificates remain incomplete |
| Statistics | PARTIALLY SUPPORTED; fitting exists, but complete observed-data provenance and diagnostics remain incomplete |
| Field variation / generalized mechanics | PARTIALLY SUPPORTED |
| Mathlib / Physlib graph-bound formalization | PARTIALLY SUPPORTED only for the narrowly guarded canonical Lean theorem families; arbitrary graph-to-Lean translation remains unsupported |

## Evidence and circularity classification

- **Same-engine consistency:** internal TensorGeometry identities and single-path SymPy checks are regression evidence, not independent verification.
- **Same engine, distinct path:** Automate Euler-Lagrange derivation versus `sympy.calculus.euler` is useful cross-checking but remains within SymPy.
- **Cross-engine:** selected tensor results are compared with EinsteinPy. Agreement is evidence, not proof.
- **Externally known results:** selected polar, sphere and Schwarzschild components are checked against analytic/textbook values recorded in tests.
- **Numerical evidence:** solver output does not establish model correctness.
- **Statistical evidence:** fit convergence does not establish physical truth; provenance must remain explicit.
- **Formal proof:** Lean CI proves the repository's submitted Lean propositions. It does not establish arbitrary graph-to-Lean proposition binding.

## Ecosystem notes

SymPy 1.14 documentation explicitly warns that `sympify()` uses `eval` and should not be used on unsanitized input. Automate's structural parser is therefore intentionally stricter than direct SymPy string parsing. citeturn457216search0turn457216search1

Mathlib4 remains actively maintained, with `v4.34.1` listed as the latest stable release at audit time and `v4.35.0-rc3` as a prerelease. Physlib is an active Lean project for digitalising physics results. These libraries are candidates for reuse only where their formal proposition genuinely matches an Automate graph claim. citeturn546223search0turn546223search8

EinsteinPy remains the intended cross-engine reference for supported symbolic differential-geometry checks. Its documentation demonstrates symbolic metric, curvature and Weyl-tensor calculations, but version/licensing details must be pinned in project metadata before being used as certificate evidence. citeturn457216search24

## Remaining work

1. Distinguish explicitly dimensionless metadata from missing/unspecified dimension metadata, so missing dimensions cannot silently pass an applicable check.
2. Expand tensor claim binding and independent EinsteinPy/textbook coverage without marking unsupported whole-tensor or index-operation claims as verified.
4. Improve SafeParser process-level resource isolation, especially true killable time/resource limits rather than post-hoc elapsed-time checks.
5. Generalize structured ODEs, mechanics, field variation, numerical convergence/error certificates and statistical provenance only where the semantics are explicit and testable.
6. Build genuine graph-to-Lean proposition translation for rules whose formal proof is claimed; reuse mathlib/physlib theorems only when proposition identity is preserved.
7. Pin external-engine versions, licenses, inputs/results and independence metadata in `docs/ECOSYSTEM.md` and verification certificates.

Claims not supported by source inspection or an executed check remain **UNVERIFIED**.
