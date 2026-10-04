# Automate Verification State

**Audit date:** 2026-10-04
**Repository:** `rynahmed101-sys/automate`
**Intended branch:** `feat/verification-hardening`
**Verified code commit:** `55d2fa3e84286a6281a828a337b22ad0afeb8b98`
**Published integration lineage:** `349b258` → recovery merge `ad702127` → upstream hardening `3e2fa552`
**Integration:** The feature branch contains the recovered local work plus the upstream hardening. No merge to `main` and no history rewrite occurred.

## Validation evidence

| Checkpoint | Result |
|---|---|
| GitHub Actions run #20, exact SHA `55d2fa3` | **PASS** |
| Python 3.10 full suite | PASS |
| Python 3.11 full suite | PASS |
| Python 3.12 full suite | PASS |
| Python 3.13 full suite | PASS |
| Explicit adversarial suite on Python 3.10–3.13 | PASS |
| Lean 4.34.1 backend proof-check job | PASS |
| Earlier exact-SHA run #19, `99ed4e1` | PASS |
| Earlier exact-SHA run #17, `58b098e` | PASS |

GitHub Actions [run #20](https://github.com/rynahmed101-sys/automate/actions/runs/37178892703) is the current exact-SHA verification for `55d2fa3`. All five jobs completed successfully.

The earlier local Windows evidence from the integrated recovery work remains separately classified: 235 passed / 1 skipped for the full suite and 30 passed / 1 skipped for the adversarial suite. The local Lean skip was caused by an unusable Lean shim/toolchain and is not evidence of local Lean proof execution.

## Hardening completed in this phase

**SafeParser security boundary.** Untrusted mathematical text is now parsed into a restricted Python AST and translated through an explicit allowlist into SymPy objects. Source strings are not passed to `sympify`/Python evaluation. Attribute access, subscripting, arbitrary callables, keyword arguments, statement-like syntax and other non-mathematical constructs are rejected. AST size/depth and resulting expression size/depth are bounded.

**Dimensional semantics.** Unknown base dimensions and unknown coordinate-dimension descriptors now fail closed instead of silently becoming dimensionless. This prevents an unrecognized unit declaration from being treated as a successful dimensionless case.

**Symbolic division.** `divide_both_sides` now requires a numeric nonzero divisor or an active trusted side condition that directly proves a symbolic divisor is nonzero. An unexplained symbolic divisor is `UNSUPPORTED`, not implicitly assumed nonzero.

**Capability honesty.** Lean capabilities in the rule registry now match the actual Lean backend scope. Only `conserve_energy`, `euler_lagrange`, and `algebraic_identity` are currently advertised as Lean-supported; arbitrary symbolic algebra rules are not falsely exposed as formally proved.

**Transactional proposal flow.** AI proposals continue to be validated, cloned, checked, and committed only after successful verification. Failed proposals leave the canonical graph unchanged.

## Current capability assessment

| Capability | Current status |
|---|---|
| AI proposal validation / transaction integrity | PARTIALLY SUPPORTED, with fail-closed capability checks and clone-before-commit |
| Safe expression parsing | PARTIALLY SUPPORTED; structural source parsing is hardened, but process-level resource isolation remains unverified |
| Algebra / ODE substitution | PARTIALLY SUPPORTED for implemented rule shapes; broad structured ODE coverage remains unverified |
| Euler-Lagrange mechanics | PARTIALLY SUPPORTED for implemented/tested systems; same-engine SymPy cross-checks are not independent engines |
| Tensor geometry | PARTIALLY SUPPORTED; TensorChecker is integrated for supported claims, with EinsteinPy cross-checks where available |
| Full 4D Schwarzschild | PARTIALLY SUPPORTED; selected components/properties are tested, not every requested property |
| Dimensions / assumptions | PARTIALLY SUPPORTED; unknown dimensions now fail closed, but there is no general assumption-entailment engine |
| Numerics | PARTIALLY SUPPORTED; numerical results are evidence, not proofs, and general error/convergence certificates remain incomplete |
| Statistics | PARTIALLY SUPPORTED; fitting exists, but complete observed-data provenance and diagnostics remain incomplete |
| Field variation / generalized mechanics | PARTIALLY SUPPORTED |
| Mathlib / Physlib graph-bound formalization | UNSUPPORTED for arbitrary graph claims; theorem reuse must preserve proposition identity |

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

1. Add a principled assumption-entailment layer instead of embedding narrow predicate checks inside individual symbolic rules.
2. Distinguish explicitly dimensionless metadata from missing/unspecified dimension metadata, so missing dimensions cannot silently pass an applicable check.
3. Expand tensor claim binding and independent EinsteinPy/textbook coverage without marking unsupported whole-tensor or index-operation claims as verified.
4. Improve SafeParser process-level resource isolation, especially true killable time/resource limits rather than post-hoc elapsed-time checks.
5. Generalize structured ODEs, mechanics, field variation, numerical convergence/error certificates and statistical provenance only where the semantics are explicit and testable.
6. Build genuine graph-to-Lean proposition translation for rules whose formal proof is claimed; reuse mathlib/physlib theorems only when proposition identity is preserved.
7. Pin external-engine versions, licenses, inputs/results and independence metadata in `docs/ECOSYSTEM.md` and verification certificates.

Claims not supported by source inspection or an executed check remain **UNVERIFIED**.
