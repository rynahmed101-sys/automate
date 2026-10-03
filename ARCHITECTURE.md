# Architecture of Automate (v0.2)

Automate is designed as an interoperability architecture rather than a new theorem prover or computer algebra system.

## 1. High-Level Architectural Flow

```
                      [ DSL / Theory File (YAML/JSON) ]
                                     │
                                     ▼
                   [ Canonical Physics IR (automate.ir) ]
                     • Expressions (Scalars, Fields, Operators, Limits, Sums)
                     • Relativistic Tensors & Einstein Summation (automate.ir.tensors)
                     • Actions, Curvature & Differential Geometry (automate.ir.actions)
                     • Units & SI Base Dimensions (automate.ir.dimensions)
                     • First-class Assumptions (m > 0, k > 0)
                                     │
                                     ▼
               [ Derivation Graph Engine (automate.core.graph) ]
                 • Nodes: Mathematical Expressions + Assumptions
                 • Edges: Transformation Rules + Justifications
                 • Hierarchical expansion (lossless macro steps)
                 • Assumption propagation & pruning queries
                 • Certificate packages with SHA-256 manifest
                                     │
        ┌────────────────────────────┴────────────────────────────┐
        ▼                                                         ▼
[ AI Subsystem (automate.ai) ]                          [ Verification Backends ]
• Context generation (automate.context.v1)    ┌───────────┬───────────┬───────────┬───────────┐
• Security validation (no eval/exec)          ▼           ▼           ▼           ▼           ▼
• Pluggable providers (Mock, Local, OpenAI) [SymPy]     [Lean 4]    [SciPy IVP] [SciPy Fit] [Dimension]
• Candidate edge ingestion                  Calculus,   Formal      Numerical   Parameter   SI base
  with AI_PROPOSED status                   Variational Theorem     Simulation  Inference   homogeneity
                                            Identities  Prover      (RK45)      (Chi-Sq)    checks
                                                          │
                                                          ▼
                                        [ Derivation Status & Artifacts ]
                                          • Strict multidimensional status taxonomy
                                          • Tamper-evident certificate package (7 files)
                                          • Interactive HTML visualization
                                          • Machine-readable JSON CLI mode (--json)
```

---

## 2. Core Modules

### `automate.ir`
* `dimensions.py`: Vector space over SI base dimensions $[M, L, T, I, \Theta, N, J]$. Parses dimension strings, performs dimensional arithmetic, and validates dimensional homogeneity.
* `assumptions.py`: First-class assumption representation. Every assumption carries an ID, mathematical predicate, category, and activation state.
* `ast.py`: Strongly-typed AST nodes (`ScalarNode`, `VariableNode`, `BinaryOpNode`, `UnaryOpNode`, `DerivativeNode`, `IntegralNode`, `TensorNode`, `ActionNode`, `MeasureNode`, `FieldNode`, `OperatorNode`, `SumNode`, `ProductNode`, `LimitNode`, `PropositionNode`).
* `tensors.py`: Relativistic and geometric tensor semantics:
  - `TensorIndex`: symbol, position (`upper` contravariant vs `lower` covariant), dummy state.
  - `TensorQuantity`: name, indices, rank, physical dimension, symmetry.
  - `validate_einstein_product`: enforces Einstein summation convention (max 2 occurrences, one upper and one lower), computes contracted resultant rank.
  - `validate_tensor_sum` and `validate_tensor_equation`: enforces strict free-index matching across addition and equations.
* `actions.py`: Differential geometry and field theory primitives:
  - `Manifold`, `CoordinateChart`, `MetricTensor`, `ChristoffelSymbols`, `RiemannTensor`, `RicciTensor`, `RicciScalar`, `EinsteinTensor`.
  - `IntegrationMeasure`, `LagrangianDensity`, `ActionFunctional`, `FunctionalDerivative`, `FieldEquation`.

### `automate.ai`
* `base.py`: Abstract `LLMProvider` interface defining `propose(context, request, options)`.
* `schemas.py`: Typed Pydantic schemas for `ProposalOrigin`, `CandidateNode`, `DerivationProposal` (`automate.proposal.v1`), and `AIContext` (`automate.context.v1`).
* `validation.py`: Zero-trust security validator. Scans raw payloads for disallowed patterns (`eval`, `exec`, `os.system`, shell metacharacters, path traversal, tokens), enforces schema compliance, validates graph prerequisites, and prevents proposals from self-assigning verified statuses.
* `context.py`: Controlled mathematical context generation. Extracts equations, active assumptions, and rule registries while strictly isolating host environment secrets and paths. Computes deterministic semantic graph hashes.
* `proposals.py`: Candidate edge ingestion and verification pipeline. Injects candidate edges with status `AI_PROPOSED`, synthesizes obligations from `RuleRegistry`, calls backends, and attaches verification evidence.
* `providers/`:
  - `mock.py`: Deterministic offline mock provider for testing and reproducible loops.
  - `local.py`: Adapter for local LLM engines (Ollama, LM Studio, llama.cpp).
  - `openai.py`: Standard API adapter using `urllib` without mandatory cloud SDK dependencies.

### `automate.core`
* `status.py`: Strict hierarchy of verification certainty (`FORMALLY_PROVED`, `SYMBOLIC_CHECKED`, `NUMERICALLY_CHECKED`, `STATISTICALLY_CHECKED`, `DIMENSIONALLY_CHECKED`, `STRUCTURALLY_VALID`, `CONDITIONAL`, `PARSED`, `AI_PROPOSED`, `UNVERIFIED`, `FAILED`, `DISPROVED`).
* `node.py`: `DerivationNode` storing the canonical expression, alternative projections (LaTeX, SymPy, Lean 4), domain, and direct/inherited assumptions.
* `edge.py`: `DerivationEdge` encapsulating transformation rules, justifications, verification status, side conditions, verification obligations, and expandable `DerivationCertificate`.
* `graph.py`: Directed Acyclic Graph manager. Enforces acyclicity, calculates topological ordering, evaluates transitive assumption dependencies, simulates assumption removal, and exports self-contained 7-file certificate packages with SHA-256 manifests.

### `automate.backend`
* `base.py`: Contract interface (`BaseChecker`, `VerificationReport`, `VerificationEvidence`).
* `dimension_backend.py`: Evaluates dimensional consistency of Euler-Lagrange equations, energy integrals, and general solutions.
* `sympy_backend.py`: Computes partial derivatives, total time derivatives, variational Euler-Lagrange equations, algebraic simplification, and zero-testing ($LHS - RHS == 0$).
* `lean_backend.py`: Translates physical and algebraic claims into formal Lean 4 theorems, invokes the Lean compiler in an isolated sandbox, parses compiler messages, and generates cryptographic certificates (SHA-256).
* `numerical_backend.py`: Solves equations of motion using SciPy `solve_ivp` (Runge-Kutta 4(5)), evaluates trajectory errors against analytical solutions, and verifies energy conservation drift.
* `statistical_backend.py`: Fits theoretical models to observational data using non-linear least squares, computes parameter standard errors, 95% confidence intervals, and $\chi^2$ goodness-of-fit.

### `automate.theory`
* `parser.py`: Translates human-readable YAML/JSON theory declarations into `DerivationGraph`.
* `rules.py`: Central registry of verified transformation rules with rich domain metadata, side conditions, and automatic verification obligation synthesis.

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
