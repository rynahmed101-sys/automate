# Automate Architecture Audit (v0.1 Prototype)

**Date**: 2026-10-03  
**Status**: Comprehensive Baseline Review  
**Objective**: Identify implemented capabilities, partial implementations, design debts, and stubs to prepare for the engineering integration phase.

---

## 1. Component Audit Matrix

| Component | Status | Detailed Finding | Remediation Plan |
| :--- | :--- | :--- | :--- |
| **`automate.ir.dimensions`** | `IMPLEMENTED` | Base SI dimensions $[M, L, T, I, \Theta, N, J]$, multiplication, division, exponentiation, string parsing, and equality. | Keep as primary dimensional engine; add unit conversions. |
| **`automate.ir.assumptions`** | `PARTIALLY_IMPLEMENTED` | `Assumption` model and `AssumptionRegistry` exist with basic metadata and active flag. | Strengthen to include category classification, predicate expressions, and condition evaluation. |
| **`automate.ir.ast`** | `PARTIALLY_IMPLEMENTED` | Classes for `SymbolNode`, `PhysicalConstant`, `DerivativeNode`, `EquationNode`, `DifferentialEquationNode`, and `MathematicalExpression`. However, `DerivationNode` uses `MathematicalExpression` with unstructured string fallback. | Upgrade `DerivationNode` to strictly distinguish `Expression`, `Equation`, `Proposition/Claim`, and `Assumption` as first-class typed variants rather than plain strings. |
| **`automate.ir.serialization`** | `IMPLEMENTED` | Stable JSON & YAML dumping/loading with `schema_version: "0.1.0"`. | Maintain; formalize with a published JSON Schema under `schemas/automate-ir-v0.1.json`. |
| **`automate.core.status`** | `DESIGN_DEBT` | Enum contains 8 statuses (`PARSED` to `FAILED`). Statuses are represented as a quasi-linear ranking, which oversimplifies formal vs empirical certainty. | Expand with `STRUCTURALLY_VALID` and `DIMENSIONALLY_CHECKED`. Separate verification evidence objects from status enum. |
| **`automate.core.node`** | `PARTIALLY_IMPLEMENTED` | Stores expression, domain, assumptions, source, representations. | Add explicit distinction for node types (`expression`, `equation`, `claim`, `assumption`, `observable`). |
| **`automate.core.edge`** | `PARTIALLY_IMPLEMENTED` | Stores input/output node IDs, rule name, justification, checker, certificate. Lacks explicit `side_conditions` and `verification_obligations`. | Add `side_conditions` (assumptions required to fire rule) and `verification_obligations` (generated mathematical claims). |
| **`automate.core.graph`** | `IMPLEMENTED` | DAG validation, topological sorting, transitive assumption queries, assumption removal simulation, and certificate macro-expansion. | Strengthen with failed derivation tracking and assumption query filters. |
| **`automate.backend.base`** | `IMPLEMENTED` | `BaseChecker` interface and `VerificationReport` data contract. | Separate verification evidence from report; record execution timestamp and artifact paths. |
| **`automate.backend.dimension_backend`**| `IMPLEMENTED` | Validates dimensional consistency for Euler-Lagrange, energy conservation, trajectory solutions, and general terms. | Expand to validate generic arbitrary equations. |
| **`automate.backend.sympy_backend`** | `IMPLEMENTED` | Verifies Euler-Lagrange derivation ($d/dt(\partial L/\partial \dot{q}) - \partial L/\partial q = 0$), energy conservation ($dE/dt = 0$ on-shell), and analytical harmonic solution. Generates 4-step certificate. | Add generic equation simplification and cancellation checking. |
| **`automate.backend.lean_backend`** | `PARTIALLY_IMPLEMENTED` | Correctly invokes local Lean 4 (`v4.34.1`), compiles Lean theorems for on-shell conservation and Euler-Lagrange algebra, records SHA-256 hash. However, continuous variational calculus is proved as an algebraic identity rather than functional analysis. | Clarify exact boundaries in docs: Lean verifies the algebraic theorem; SymPy checks continuous differentiation. Do not overclaim full calculus formalization. |
| **`automate.backend.numerical_backend`**| `IMPLEMENTED` | Solves ODE via SciPy `solve_ivp` (RK45), evaluates max error, RMSE, and relative energy drift ($\Delta E / E_0$). | Add customizable time spans and tolerances via parameters. |
| **`automate.backend.statistical_backend`**| `IMPLEMENTED` | Performs non-linear least squares fit with SciPy `curve_fit`, standard errors, 95% confidence intervals, reduced $\chi^2$, and $R^2$. | Keep clean separation between empirical evidence and deductive proof. |
| **`automate.theory.parser`** | `IMPLEMENTED` | Parses YAML/JSON theory declarations into `DerivationGraph`. | Support side conditions and verification obligations. |
| **`automate.theory.rules`** | `PARTIALLY_IMPLEMENTED` | Rule registry has 6 rules. | Add side condition requirements (e.g. division requires non-zero divisor). |
| **`automate.visualization.html_graph`** | `IMPLEMENTED` | Standalone interactive HTML with vis.js, color-coded statuses, and node/edge inspector panels. | Keep maintained and self-contained. |
| **`automate.visualization.terminal`** | `IMPLEMENTED` | Formatted Rich tables, assumption impact summary, verification matrix with console-safe symbols. | Keep maintained. |
| **`automate.cli`** | `IMPLEMENTED` | Subcommands: `demo`, `parse`, `check`, `prove`, `simulate`, `stats`, `query-assumptions`, `expand`, `visualize`, `report`. | Add `export-certificate` and import/export subcommands. |
| **`automate.demo`** | `IMPLEMENTED` | Runs end-to-end harmonic oscillator derivation through all backends and produces reports. | Expand with side conditions and certificate bundle export. |

---

## 2. Integrity and Truthfulness Assessment

1. **What is genuinely verified**:
   - `DimensionChecker` verifies $[L] = \text{Joules}$, $[EoM] = \text{Newtons}$, $[E] = \text{Joules}$, $[x] = \text{meters}$.
   - `SymPyChecker` verifies the symbolic Euler-Lagrange operations, ODE residual zero-testing, and energy invariance.
   - `LeanChecker` compiles and type-checks the theorem in Lean 4 without error.
   - `NumericalChecker` verifies trajectory error ($\text{RMSE} < 10^{-7}$) and energy drift ($\Delta E/E_0 < 10^{-7}$).
   - `StatisticalChecker` estimates $\omega \approx 2.0$ with valid $\chi^2$ and $R^2 > 0.99$.
2. **What must NOT be claimed**:
   - *False Claim to Avoid*: "Lean 4 has proved the Euler-Lagrange theorem from first principles of functional analysis."
   - *Reality*: Lean 4 proved that *given* the momentum and force definitions, the subtraction equates to the equation of motion, and *given* the equation of motion, the energy derivative vanishes. The variational principle itself is evaluated via SymPy.
3. **Design Debts to Address**:
   - Missing explicit separation of `Expression`, `Equation`, `Claim`, `Assumption` in IR.
   - Missing side-condition tracking (e.g., $f \neq 0$ when dividing by $f$).
   - Lack of a standardized `certificate/` artifact export directory.
   - Missing formal JSON Schema (`schemas/automate-ir-v0.1.json`).

---

## 3. Action Items for Integration Phase

1. **Phase 2 & 3**: Refactor IR nodes to formally separate Expressions, Equations, Claims, and Assumptions; implement Side Conditions and Verification Obligations on Edges.
2. **Phase 4**: Formalize lossless macro expansion and test equivalence.
3. **Phase 5**: Expand status hierarchy (`STRUCTURALLY_VALID`, `DIMENSIONALLY_CHECKED`) and decouple verification evidence.
4. **Phase 7**: Author `docs/ECOSYSTEM.md` surveying adjacent open-source projects.
5. **Phase 8 & 9**: Implement JSON Schema validation and round-trip serialization tests.
6. **Phase 10**: Implement standardized certificate bundle generation (`export_certificate`).
7. **Phase 11 & 12**: Implement failed derivation preservation and advanced assumption query filters.
8. **Phase 13 & 14**: Expand test suite to cover all 19 test categories and run the strengthened demo.
