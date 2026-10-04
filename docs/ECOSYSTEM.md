# Mathematical & Scientific Computing Ecosystem Audit

**Project**: Automate (Verification Orchestration for Mathematics & Physics)  
**Date**: 2026-10-04  
**License**: Apache-2.0  
**Core Mandate**: Automate is an independent verification orchestrator, canonical representation layer, and provenance engine. It wraps and cross-checks mature open-source mathematical systems rather than building a redundant Computer Algebra System (CAS).

---

## 1. Architectural Philosophy: The Multi-Engine Verification Protocol

```
                        AI PROPOSAL / USER INPUT
                                   │
                                   ▼
                    ┌───────────────────────────────┐
                    │      Automate IR Pipeline     │
                    │  (SafeParser, AST, Validation)│
                    └──────────────┬────────────────┘
                                   │
                                   ▼
                    ┌───────────────────────────────┐
                    │       Derivation Graph        │
                    │  (Nodes, Edges, Assumptions)  │
                    └──────────────┬────────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐             ┌──────────────┐
│ Primary CAS  │            │ Cross-Check  │             │ Formal Proof │
│ (e.g. SymPy) │            │ (EinsteinPy) │             │ (Lean4 /     │
│              │            │              │             │  Mathlib4)   │
└──────┬───────┘            └──────┬───────┘             └──────┬───────┘
       │                           │                            │
       └───────────────────────────┼────────────────────────────┘
                                   │
                                   ▼
                    ┌───────────────────────────────┐
                    │       Evidence Package        │
                    │  (Independence Class, Hashes, │
                    │   Discrepancy Diagnostics)    │
                    └───────────────────────────────┘
```

1. **Agreement is Evidence, Not Proof**: When SymPy and EinsteinPy produce the identical Riemann tensor for a metric, that agreement is strong computational evidence against implementation bugs, but not an axiomatic proof.
2. **Formal Proofs Must Bind to the Graph**: A Lean 4 certificate is only valid if the formal proposition was synthesized from the actual graph expression AST, not from a disconnected canned template.
3. **No Silent Fallback**: Unknown checkers are rejected. Rules declare `allowed_checkers`; attempting to run an unsupported checker (e.g. `dimension` for `euler_lagrange`) is immediately halted.

---

## 2. Comprehensive Inventory of Mathematical Engines

### 2.1 SymPy
* **Project**: SymPy
* **Repository**: `https://github.com/sympy/sympy`
* **Purpose**: Symbolic mathematics, expression manipulation, calculus of variations (`sympy.calculus.euler.euler_equations`), mechanics equations of motion (`LagrangesMethod`, `KanesMethod`), ODE substitution, polynomial algebra, matrix operations.
* **Version**: `1.14.0` in the current CI/runtime environment; the dependency is floor-pinned as `sympy>=1.12`.
* **License**: BSD-3-Clause (Permissive, fully compatible with Apache-2.0).
* **Integration Method**: Python library API integration.
* **Vendored or External**: External runtime dependency.
* **Runtime vs CI**: Direct runtime dependency.
* **Input Representation**: SymPy `Basic` / `Expr` objects created strictly via Automate's `SafeParser` (never raw string `eval` or unguarded `sympify`).
* **Output Representation**: Symbolic expressions, equations (`sp.Eq`), matrices (`sp.Matrix`).
* **Conversions Performed**: String expression → `SafeParser` AST validation → SymPy expression tree → simplification and residual evaluation.
* **Known Limitations**:
  - `sp.sympify` internally utilizes Python AST and compilation machinery; it must NEVER be exposed as a public untrusted boundary.
  - Large tensor contractions (4D metrics with off-diagonal terms) can cause exponential expansion if not factored or simplified selectively.

### 2.2 EinsteinPy
* **Project**: EinsteinPy
* **Repository**: `https://github.com/einsteinpy/einsteinpy`
* **Purpose**: Relativistic geometry and general relativity. Calculation of Christoffel symbols, Riemann curvature tensor, Ricci tensor, Ricci scalar, Einstein tensor, predefined Schwarzschild metric, and geodesic equations.
* **Version**: `0.4.0`
* **License**: MIT (Permissive, fully compatible with Apache-2.0).
* **Integration Method**: External verification oracle via `einsteinpy.symbolic` adapter (`automate/tensors/einsteinpy_adapter.py`).
* **Vendored or External**: External dependency.
* **Runtime vs CI**: Runtime optional / CI cross-validation oracle.
* **Input Representation**: SymPy coordinate symbols and `sp.Matrix` metric tensor.
* **Output Representation**: EinsteinPy `MetricTensor`, `ChristoffelSymbols`, `RiemannCurvatureTensor`, `RicciTensor`, `RicciScalar`, `EinsteinTensor`.
* **Conversions Performed**: Automate `TensorGeometry` metric $\leftrightarrow$ EinsteinPy `MetricTensor` $\leftrightarrow$ array extraction for cross-comparison.
* **Known Limitations**:
  - Predefined coordinates often use fixed naming conventions $(t, r, \theta, \phi)$; coordinate re-mapping is required when users supply custom symbols.
  - Computation is synchronous and can be computationally demanding for non-vacuum metrics.

### 2.3 Cadabra2
* **Project**: Cadabra2
* **Repository**: `https://github.com/kpeeters/cadabra2`
* **Purpose**: Specialized computer algebra system designed for quantum field theory, multi-term tensor symmetries, Young tableaux, Bianchi identities, Fierz transformations, and exterior algebra.
* **Version**: `2.x`
* **License**: **GPL-3.0** (Copyleft).
* **Licensing Boundary with Automate (Apache-2.0)**:
  - **ABSOLUTE RULE**: NO Cadabra2 source code may be vendored or copied into Automate.
  - Integration is strictly through an **external tool/subprocess boundary** or CI validation runner.
  - Automate can generate Cadabra scripts (`.cdb`), execute Cadabra as an external CLI process via stdin/stdout, and parse the verified tensor identities.
  - If Cadabra is not installed on the host system, Cadabra-dependent verification steps return `NOT_APPLICABLE` or `UNVERIFIED` with a descriptive message.
* **Input Representation**: Cadabra tensor markup script.
* **Output Representation**: ASCII / LaTeX output from Cadabra process execution.
* **Known Limitations**:
  - Requires native C++/Python compilation on Windows; primarily practical in Linux CI containers.

### 2.4 Lean 4, Mathlib4 & Physlib
* **Project**: Lean 4, Mathlib4, Physlib
* **Repositories**:
  - Lean 4: `https://github.com/leanprover/lean4`
  - Mathlib4: `https://github.com/leanprover-community/mathlib4`
  - Physlib: `https://github.com/leanprover-community/physlib`
* **Purpose**: Interactive theorem proving, dependent type theory, verified mathematical structures (Mathlib4), and formalized theoretical physics (Physlib).
* **Version**: Lean `v4.34.1`
* **License**: Apache-2.0 (Directly compatible with Automate).
* **Integration Method**: External process execution (`lean` compiler binary) invoked on generated `.lean` source files.
* **Vendored or External**: External dependency managed via `elan`.
* **Runtime vs CI**: External toolchain; verified in CI container environment.
* **Input Representation**: Synthesized Lean 4 theorem declarations containing hypotheses and equation definitions derived from the Automate IR.
* **Output Representation**: Lean compiler exit code (0 for proven, non-zero for syntax or tactic failure) and proof diagnostic logs.
* **Conversions Performed**: Automate Expression AST $\to$ Lean 4 term syntax (e.g. `Real` arithmetic, derivatives, ODE residuals).
* **Known Limitations**:
  - Toolchain initialization is slow.
  - Proof automation for non-linear differential equations requires specialized tactics or manual certificate synthesis.
  - `elan` shims on Windows can lead to false-positive availability detection if toolchains are uninstalled.

### 2.5 SciPy & NumPy
* **Project**: SciPy, NumPy
* **Repositories**:
  - `https://github.com/scipy/scipy`
  - `https://github.com/numpy/numpy`
* **Purpose**: Numerical initial value problem integration (`scipy.integrate.solve_ivp`), boundary value problems (`solve_bvp`), numerical quadrature (`quad`), non-linear least squares (`scipy.optimize.curve_fit`), roots, eigenvalues.
* **Version**: SciPy `1.18.1` is the latest upstream release as of 2026-10-04; Automate's dependency is unpinned above `1.10`, so CI resolves versions per Python environment. NumPy `2.5.3` is present in the current Python 3.13 CI environment.
* **License**: BSD-3-Clause (Permissive, Apache-2.0 compatible).
* **Integration Method**: Direct Python API.
* **Vendored or External**: External runtime dependencies.
* **Runtime vs CI**: Runtime dependency.
* **Input Representation**: Vectorized Python callables generated via `sp.lambdify` or NumPy array functions.
* **Output Representation**: `OdeResult`, `OptimizeResult`, numerical trajectory arrays.
* **Conversions Performed**: Symbolic EoM $\to$ first-order ODE vector field $\dot{y} = f(t, y) \to$ RK45 numerical solver $\to$ trajectory and energy drift report.
* **Known Limitations**:
  - Numerical integration is an empirical check of trajectory stability, NOT an exact mathematical proof.
  - Truncation error, step-size stiffness, and tolerance parameters must be explicitly certified.

### 2.6 lmfit & statsmodels
* **Project**: lmfit & statsmodels
* **Repositories**:
  - lmfit: `https://github.com/lmfit/lmfit-py`
  - statsmodels: `https://github.com/statsmodels/statsmodels`
* **Purpose**: Advanced non-linear parameter estimation, parameter bounds, linear/non-linear constraints, confidence intervals, covariance analysis, AIC/BIC model comparison.
* **Version**: lmfit `1.3.4`; statsmodels `0.15.0` is the current upstream release, but statsmodels is not a direct Automate dependency.
* **License**: BSD-3-Clause (Permissive, Apache-2.0 compatible).
* **Integration Method**: Python library API.
* **Vendored or External**: External dependency.
* **Runtime vs CI**: Optional runtime / statistical backend enhancement.
* **Input Representation**: Empirical data vectors $(x_i, y_i, \sigma_i)$, parameter bounds, model functions.
* **Output Representation**: `ModelResult` with full covariance matrix, standard errors, residual diagnostics.
* **Conversions Performed**: Automate model string $\to$ parameter constraint graph $\to$ Levenberg-Marquardt / Nelder-Mead optimization.
* **Known Limitations**:
  - Convergence of a fit to empirical data establishes consistency under assumptions, not fundamental physical truth.
  - Synthetic data must be explicitly flagged and segregated from real empirical measurements.

### 2.7 Pint
* **Project**: Pint
* **Repository**: `https://github.com/hgrecco/pint`
* **Purpose**: Unit definitions, physical quantities, dimensional analysis, Buckingham-$\pi$ theorem reductions, and unit conversions.
* **Version**: Pint `0.26.1` for Python >=3.12; current CI resolves Pint `0.25.3` on Python 3.10/3.11 because the latest Pint release requires Python >=3.12.
* **License**: BSD-3-Clause (Permissive, Apache-2.0 compatible).
* **Integration Method**: External dependency augmenting Automate's native `Dimension` type.
* **Vendored or External**: External dependency.
* **Runtime vs CI**: Optional runtime enhancement.
* **Input Representation**: String expressions with unit tags (e.g. `meter / second**2`).
* **Output Representation**: `pint.Quantity` objects with dimensionality mapping.
* **Known Limitations**:
  - Dimensionless angles (radians) and phases must be handled with explicit physical semantics to avoid conflating torque ($N\cdot m$) and energy ($J$).

### 2.8 SciLean
* **Project**: SciLean
* **Repository**: `https://github.com/lecopivo/SciLean`
* **Purpose**: Scientific computing in Lean 4. Differentiable programming, symbolic differentiation, automatic differentiation, and verified numerical integration.
* **License**: MIT (Permissive, Apache-2.0 compatible).
* **Integration Method**: External Lean package for formal numerical proofs.
* **Vendored or External**: External toolchain package.
* **Runtime vs CI**: Future formal verification research track.

---

## 3. Fresh Upstream Verification

The following facts were checked against upstream release pages on 2026-10-04 and are intentionally separated from Automate's resolved CI environment:

| System | Freshly verified upstream fact | Source |
|---|---|---|
| SciPy | 1.18.1 released 2026-08-21; current latest release listed by SciPy | https://scipy.org/news/ |
| EinsteinPy | 0.4.0; MIT license; latest PyPI release dated 2021-05-05 | https://pypi.org/project/einsteinpy/ |
| Lean 4 | 4.34.1 is the latest stable release listed; 4.35.0-rc3 is a prerelease | https://lean-lang.org/doc/reference/latest/releases/ |
| Mathlib4 | v4.34.1 listed as stable; v4.35.0-rc3 listed as prerelease | https://github.com/leanprover-community/mathlib4/releases |
| lmfit | 1.3.4; BSD-3-Clause; latest PyPI release dated 2025-07-19 | https://pypi.org/project/lmfit/ |
| statsmodels | 0.15.0; BSD-3-Clause; latest PyPI release dated 2026-08-27 | https://pypi.org/project/statsmodels/ |
| Pint | 0.26.1; BSD license; requires Python >=3.12 | https://pypi.org/project/Pint/ |

CI should still record the exact resolved version actually used for each verification run; upstream “latest” is not a substitute for runtime provenance.

## 4. Dependency & License Compliance Matrix

| Software | Repository | License | Integration Boundary | License Conflict? | Role in Automate |
|---|---|---|---|---|---|
| **SymPy** | `sympy/sympy` | BSD-3-Clause | Python API | None | Primary symbolic CAS backend |
| **SciPy** | `scipy/scipy` | BSD-3-Clause | Python API | None | Primary numerical ODE/optimization backend |
| **NumPy** | `numpy/numpy` | BSD-3-Clause | Python API | None | Array foundation for numerics |
| **EinsteinPy** | `einsteinpy/einsteinpy` | MIT | Python API | None | Relativistic tensor verification oracle |
| **Pint** | `hgrecco/pint` | BSD-3-Clause | Python API | None | Advanced unit and dimensional analysis |
| **lmfit** | `lmfit/lmfit-py` | BSD-3-Clause | Python API | None | Statistical model fitting and parameter bounds |
| **statsmodels** | `statsmodels/statsmodels`| BSD-3-Clause | Python API | None | Advanced econometric/time-series statistical oracle |
| **Mathlib4** | `leanprover-community/mathlib4` | Apache-2.0 | Lean compiler CLI | None | Formal mathematical theorem library |
| **Physlib** | `leanprover-community/physlib` | Apache-2.0 | Lean compiler CLI | None | Formal physics theorem library |
| **Cadabra2** | `kpeeters/cadabra2` | **GPL-3.0** | Subprocess / CLI only | **Strict Boundary**: NO vendoring; CLI oracle only | Optional tensor identity oracle |

---

## Cadabra2 integration boundary

The repository now contains a bounded Cadabra2 adapter at
`automate/tensors/cadabra_adapter.py`. Cadabra remains an external CLI
oracle: no Cadabra source or runtime is vendored into Automate. The adapter
uses `VerifiedExecutionSandbox`, records the executable/version and exact
source fingerprint, bounds serialized output, and distinguishes unavailable,
unsupported, execution-failed, discrepancy, and independent-agreement paths.

The adapter now sits behind a graph-bound canonical Tensor IR bridge.
Structured graph AST tensor/symbol nodes are converted losslessly within a
strict supported subset, preserving factor identity and index variance while
refusing unsupported operations and missing structured AST data.

The end-to-end verification API in
`automate/tensors/cadabra_verification.py` performs graph AST -> canonical
Tensor IR -> deterministic Cadabra source -> canonical IR fingerprint ->
bounded Cadabra execution -> provenance-bound evidence. Its comparison target
is generated internally by a separate structural renderer rather than supplied
by the caller. Agreement is classified as `DIFFERENT_ENGINE` only for this
explicit structural round-trip scope; it is not presented as a general
mathematical proof. Extending this to semantic tensor identities requires an
independent result computation and explicit index/symmetry metadata.

## 5. Trust and Provenance Hierarchy

Automate assigns every verification result an explicit `independence_class`:

1. **`FORMAL_PROOF`**:
   - The proposition was translated into formal type theory (Lean 4) and checked by the independent Lean kernel without axioms or tautologies.
2. **`EXTERNALLY_KNOWN_RESULT`**:
   - The result is checked against pre-computed textbook analytic values (e.g. Carroll eq 5.49, MTW §8.6).
3. **`DIFFERENT_ENGINE`**:
   - The calculation was performed by Automate's native engine and independently cross-checked against a distinct third-party engine (e.g. Automate `TensorGeometry` vs `EinsteinPy`).
4. **`SAME_ENGINE`**:
   - The calculation and validation were performed using the same underlying library (e.g. SymPy verifying SymPy output). Useful for regression testing, but labeled as **consistency evidence**, never independent proof.
5. **`NUMERICAL_EVIDENCE`**:
   - Trajectory integration (SciPy `solve_ivp`) showing convergence and bounded energy drift.
6. **`STATISTICAL_EVIDENCE`**:
   - Non-linear regression (SciPy / lmfit) on explicitly labeled `OBSERVED_DATA` or `SYNTHETIC_BENCHMARK`.
