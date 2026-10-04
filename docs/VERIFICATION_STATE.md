# Automate Verification State Audit

**Generated**: 2026-10-04  
**Audit Target**: `feat/verification-orchestrator` (branched from `feat/verification-hardening` at `1948ef94b57effafb0e8c084e2c9854ab5cdcb6d`)  
**Base Commit**: `1948ef94b57effafb0e8c084e2c9854ab5cdcb6d`  
**Previous Audit Report Baseline**: 172 passed, 1 skipped (Commit `172a9aa` / earlier `c6ab3eb`)  
**Actual Live Test State**: **198 passed, 1 skipped (Total: 199 tests)**

---

## 1. Commit and Branch Identification

| Metric | Value |
|---|---|
| Current Working Branch | `feat/verification-orchestrator` |
| Upstream Feature Branch | `feat/verification-hardening` |
| Current Commit SHA | `1948ef94b57effafb0e8c084e2c9854ab5cdcb6d` |
| Previous Hardening Commit | `172a9aa5231c51f04db0e68e1abecb07b14a2f8f` |
| Baseline Commit | `a93c9bd3e24bf81f4dd07e986548489659a4cbc8` |

### Commits on `feat/verification-hardening` since `a93c9bd`:
1. `c6ab3eb`: `security+dispatch: SafeParser, remove generic fallback, fix transactions`
2. `172a9aa`: `tensors: replace circular tests with independent analytic ground truth`
3. `1948ef9`: `security+algebra: SafeParser wired into ODE verifier; 4 algebraic rules implemented`

---

## 2. GitHub Actions CI Status

* **Latest CI Execution in GitHub Actions**:
  - Run ID: `37155684760`
  - Trigger Branch: `feat/generalized-engine`
  - Trigger Commit: `a93c9bd3e24bf81f4dd07e986548489659a4cbc8`
  - Status: `completed`
  - Conclusion: `success`
* **CI Execution for Commit `1948ef94b5...`**: **NONE (UNVERIFIED by CI)**.
  - Reason: `.github/workflows/ci.yml` line 5 restricted push triggers to `feat/generalized-engine` and `main`.
  - Neither `feat/verification-hardening` nor `feat/verification-orchestrator` were configured in the CI push trigger.
  - Therefore, commits `c6ab3eb`, `172a9aa`, and `1948ef9` have **never been executed by GitHub Actions CI**.
* **Python Versions Tested**:
  - Locally: Python 3.13.13 (win32)
  - CI Matrix (configured, but unexecuted on current commit): Python 3.10, 3.11, 3.12, 3.13 on `ubuntu-latest`.
* **Lean 4 Version Tested**:
  - Locally: Lean toolchain is NOT configured (elan shim present, but `elan default` not set).
  - CI Matrix: Lean 4.34.1 configured, but job is restricted to PRs or pushes to `main` (unexecuted).

---

## 3. Test Suite Inventory

Total tests collected: **199 tests** across 21 test modules.
Local execution result: **198 PASSED, 1 SKIPPED** in 35.52s.

### Test Count Breakdown by Module

| Test Module | Total Tests | Passed | Skipped | Status |
|---|---|---|---|---|
| `tests/test_adversarial.py` | 27 | 26 | 1 | PASSED (1 skip) |
| `tests/test_ai.py` | 7 | 7 | 0 | PASSED |
| `tests/test_algebraic_rules.py` | 26 | 26 | 0 | PASSED |
| `tests/test_assumptions.py` | 6 | 6 | 0 | PASSED |
| `tests/test_cli_json.py` | 5 | 5 | 0 | PASSED |
| `tests/test_end_to_end.py` | 1 | 1 | 0 | PASSED |
| `tests/test_field_theory.py` | 5 | 5 | 0 | PASSED |
| `tests/test_field_theory_general.py` | 4 | 4 | 0 | PASSED |
| `tests/test_graph.py` | 4 | 4 | 0 | PASSED |
| `tests/test_ir.py` | 4 | 4 | 0 | PASSED |
| `tests/test_lean_backend.py` | 3 | 3 | 0 | PASSED |
| `tests/test_mechanics_general.py` | 5 | 5 | 0 | PASSED |
| `tests/test_numerical_backend.py` | 3 | 3 | 0 | PASSED |
| `tests/test_safe_parser.py` | 50 | 50 | 0 | PASSED |
| `tests/test_schema.py` | 3 | 3 | 0 | PASSED |
| `tests/test_serialization_roundtrip.py` | 3 | 3 | 0 | PASSED |
| `tests/test_statistical_backend.py` | 2 | 2 | 0 | PASSED |
| `tests/test_sympy_backend.py` | 4 | 4 | 0 | PASSED |
| `tests/test_tensor_algebra.py` | 24 | 24 | 0 | PASSED |
| `tests/test_tensors.py` | 7 | 7 | 0 | PASSED |
| `tests/test_transaction_integrity.py` | 11 | 11 | 0 | PASSED |
| **TOTAL** | **199** | **198** | **1** | **PASSED** |

### Skipped Tests

1. `tests/test_adversarial.py::TestLeanBackendSecurity::test_lean_supported_rules_are_not_fabricated_without_lean`
   - **Skip Message**: `Lean 4 is installed; this test is for no-Lean environments only.`
   - **Root Cause**: `LeanChecker.is_available()` returns `True` if `lean.exe` exists on PATH. On Windows, `elan` places a shim executable `lean.exe` in `~/.elan/bin`, but executing `lean --version` fails because no toolchain is configured (`error: no default toolchain configured`). Thus `is_available()` has a false-positive detection bug.

---

## 4. Unsupported Capabilities

1. **Tensor Backend Integration**:
   - `TensorGeometry` (`automate/tensors/algebra.py`) is a standalone symbolic module.
   - It is NOT connected to `BaseChecker` or `DerivationGraph` dispatch.
   - There is no `TensorChecker` class in `automate/backend/`.
   - Tensor rules (`index_contract`, `raise_index`, `lower_index`) dispatch to SymPy, returning `NOT_APPLICABLE` or falling through.
2. **Checker Capability Enforcement**:
   - `RuleDefinition.allowed_checkers` was introduced in commit `c6ab3eb`.
   - However, `automate/ai/proposals.py` only validates that `target_checker in _KNOWN_CHECKERS`.
   - It does NOT check `proposal.target_checker in rule_def.allowed_checkers`.
   - As a result, proposals specifying incompatible checkers (e.g., target_checker="dimension" for euler_lagrange) can bypass rule constraints.
3. **Formal Proof Graph Binding**:
   - The Lean backend emits fixed template theorems for 1D harmonic oscillator equations.
   - The emitted Lean formal proposition does NOT reflect the actual graph AST of general Lagrangians or equations of motion.
   - Modifying the graph proposition does not change the emitted Lean theorem; this produces false formal certainty.
4. **Dimension Analysis Granularity**:
   - Unannotated variables are implicitly treated as dimensionless rather than `UNKNOWN_DIMENSION`.
   - Dimensional analysis cannot represent angles/phases with physical rigor.
5. **Full 4D Relativistic Metrics**:
   - Full 4D Schwarzschild, Kerr, and cosmological metrics are not verified in the test suite due to expensive symbolic expansion. Only 2D reductions and polar/spherical coordinates are verified.
6. **Real Empirical Data Verification**:
   - The statistical backend generates synthetic data if observations are not provided.
   - It does not distinguish synthetic benchmarks from verified empirical evidence in its immutable certificate metadata.

---

## 5. Known Verification Weaknesses

1. **SafeParser Call-Site Gaps**:
   - `SafeParser` is enforced in `_verify_algebraic_identity`, `_verify_ode_solution`, and the 4 algebraic rule verifiers (`divide_both_sides`, `differentiate_both_sides`, `substitute`, `simplify`).
   - `SafeParser` is **NOT yet wired into**:
     * `automate/mechanics/lagrangian.py::_parse_expression` (uses raw `sp.sympify`)
     * `automate/field_theory/variational.py::_parse_expression` (uses raw `sp.sympify`)
     * `automate/backend/numerical_backend.py` EoM extraction (uses raw `sp.sympify`)
     * `automate/backend/statistical_backend.py` expression model parsing (uses raw `sp.sympify`)
2. **Lean Availability False-Positive**:
   - `LeanChecker.is_available()` returns `True` based on `os.path.exists` on the binary shim without checking execution return code or toolchain readiness.
3. **Assumption Reasoning Gaps**:
   - Assumptions such as `{"m": "positive"}` are passed as constructor flags to SymPy symbols.
   - They are not reasoned about formally to establish non-zero constraints (e.g. `m != 0`) before division operations.

---

## 6. Known Circularity Risks

| Test / Path | Classification | Risk Description |
|---|---|---|
| `test_einstein_tensor_sphere` | **CONSISTENCY ONLY** | Evaluates $G_{\mu\nu}$ against $R_{\mu\nu} - \frac{1}{2}g_{\mu\nu}R$ using the identical `TensorGeometry` instance. Proves internal formula implementation, not external geometric truth. |
| `test_bianchi_identity_flat/sphere/polar` | **PARTIALLY CONSISTENCY** | Tests contracted Bianchi identity using tensors computed by the same engine. |
| `statistical_backend` synthetic fit | **NUMERICAL EVIDENCE ONLY** | Fits a function to synthetic data generated from the same function. Proves SciPy curve_fit converges, not that the model is physically valid. |
| `lean_backend` 1D SHO template | **DISCONNECTED FORMAL** | Emits a static Lean proof that does not vary when the derivation graph's Lagrangian expression is altered. |

---

## 7. Audit Conclusion

The codebase has reached **198 passing tests** with essential initial security hardening (`SafeParser`) and transaction isolation (clone-before-mutation). However:
1. CI has never run on commits `c6ab3eb`, `172a9aa`, or `1948ef9`.
2. Tensor verification is an unintegrated standalone calculation module, not a graph checker.
3. Checker capability constraints are declared in `RuleDefinition` but not enforced in `apply_and_verify_proposal`.
4. Lean proofs are disconnected from graph expressions.
5. The remaining `sp.sympify` call-sites must be unified under the AST/SafeParser boundary.
