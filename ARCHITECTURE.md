# Architecture of Automate

Automate is designed as an interoperability architecture rather than a new theorem prover or computer algebra system.

## 1. High-Level Architectural Flow

```
                      [ DSL / Theory File (YAML/JSON) ]
                                     │
                                     ▼
                   [ Canonical Physics IR (automate.ir) ]
                     • Expressions (Scalars, Vectors, Tensors)
                     • Derivatives, Integrals, Differential Eqs
                     • Units & Dimensions
                     • First-class Assumptions (m > 0, k > 0)
                                     │
                                     ▼
               [ Derivation Graph Engine (automate.core.graph) ]
                 • Nodes: Mathematical Expressions + Assumptions
                 • Edges: Transformation Rules + Justifications
                 • Hierarchical expansion (lossless macro steps)
                 • Assumption propagation & pruning queries
                                     │
                                     ▼
                     [ Pluggable Verification Backends ]
         ┌───────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
         ▼               ▼              ▼              ▼              ▼              ▼
     [ SymPy ]       [ Lean 4 ]     [ Numerical ]   [ Statistical] [ Dimension ]  [ Future: ]
     Algebraic,      Formal Proof   SciPy/NumPy     Parameter      Unit consistency Z3, Physlib
     Calculus, &     Obligations    Simulation &    Inference &    [M][L][T]^-2
     Euler-Lagrange  & Theorems     ODE error       Residuals
                                     │
                                     ▼
                   [ Derivation Status & Artifacts ]
                     • PARSED / SYMBOLIC_CHECKED / NUMERICALLY_CHECKED
                     • STATISTICALLY_CHECKED / FORMALLY_PROVED / CONDITIONAL / FAILED
                     • Interactive HTML / SVG Graph Visualization
                     • Machine-readable JSON / YAML Execution Reports
```

---

## 2. Core Modules

### `automate.ir`
* `dimensions.py`: Vector space over SI base dimensions $[M, L, T, I, \Theta, N, J]$. Parses dimension strings, performs dimensional arithmetic, and validates dimensional homogeneity.
* `assumptions.py`: First-class assumption representation. Every assumption carries an ID, mathematical predicate, and activation state.
* `ast.py`: Strongly-typed AST nodes (`MathematicalExpression`, `SymbolNode`, `DerivativeNode`, `DifferentialEquationNode`, `StatisticalModelNode`).
* `serialization.py`: Stable JSON and YAML serializer adhering to `schema_version: "0.1.0"`.

### `automate.core`
* `status.py`: Strict hierarchy of verification certainty.
* `node.py`: `DerivationNode` storing the canonical expression, alternative projections (LaTeX, SymPy, Lean 4), domain, and direct/inherited assumptions.
* `edge.py`: `DerivationEdge` encapsulating transformation rules, justifications, verification status, and expandable `DerivationCertificate`.
* `graph.py`: Directed Acyclic Graph manager. Enforces acyclicity, calculates topological ordering, evaluates transitive assumption dependencies, and simulates the impact of dropping assumptions.

### `automate.backend`
* `base.py`: Contract interface (`BaseChecker`, `VerificationReport`).
* `dimension_backend.py`: Evaluates dimensional consistency of Euler-Lagrange equations, energy integrals, and general solutions.
* `sympy_backend.py`: Computes partial derivatives, total time derivatives, variational Euler-Lagrange equations, algebraic simplification, and zero-testing ($LHS - RHS == 0$).
* `lean_backend.py`: Translates physical and algebraic claims into formal Lean 4 theorems, invokes the Lean compiler in an isolated sandbox, parses compiler messages, and generates cryptographic certificates (SHA-256).
* `numerical_backend.py`: Solves equations of motion using SciPy `solve_ivp` (Runge-Kutta 4(5)), evaluates trajectory errors against analytical solutions, and verifies energy conservation drift.
* `statistical_backend.py`: Fits theoretical models to observational data using non-linear least squares, computes parameter standard errors, 95% confidence intervals, and $\chi^2$ goodness-of-fit.

### `automate.theory`
* `parser.py`: Translates human-readable YAML/JSON theory declarations into `DerivationGraph`.
* `rules.py`: Registry of verified mathematical physics transformation rules.

### `automate.visualization`
* `html_graph.py`: Generates interactive HTML graph visualizations with vis.js, color-coded by verification status with interactive formula and certificate inspection.
* `terminal.py`: Formatted terminal tables and assumption reports using Rich.

---

## 3. Lossless Mathematical Macro-Expansion
To prevent 1000-step human derivations, Automate allows users to specify high-level transformations:
$$A \xrightarrow{\text{Euler-Lagrange}} B$$
Under the hood, the backend generates an expandable certificate:
1. $p = \frac{\partial L}{\partial \dot{x}} = m\dot{x}$
2. $\dot{p} = \frac{d}{dt}(m\dot{x}) = m\ddot{x}$
3. $F = \frac{\partial L}{\partial x} = -kx$
4. $\dot{p} - F = m\ddot{x} - (-kx) = m\ddot{x} + kx = 0$

When requested (`automate expand graph.json --edge edge_euler_lagrange`), Automate unpacks the certificate into a verifiable sub-graph without losing provenance.
