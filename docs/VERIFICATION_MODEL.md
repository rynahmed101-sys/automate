# Automate Verification Model & Status Taxonomy

Automate rejects the practice of collapsing heterogeneous scientific checks into a single scalar "proof percentage" (e.g. "87% proved"). In mathematical physics, different verification backends answer fundamentally different epistemic questions:

1. **Formal Theorem Proving (Lean 4)** establishes deductive truth from axioms in a sound type theory (dependent type theory with proof irrelevance and classical choice).
2. **Computer Algebra (SymPy)** verifies algebraic identities and symbolic calculus up to symbolic simplifications and branch cuts.
3. **Numerical Differential Equations (SciPy RK45)** validates that an analytical trajectory satisfies an Initial Value Problem within floating-point tolerance $\epsilon$.
4. **Statistical Inference (SciPy)** validates parameter consistency against observational or synthetic datasets under hypothesis tests and confidence intervals.
5. **Dimensional Analysis** guarantees homogeneity across the seven base SI physical dimensions.

Conflating these distinct evidence dimensions into an arbitrary percentage is mathematically misleading. Automate preserves the **multidimensional evidence vector** for every derivation step.

---

## 1. Verification Status Taxonomy (`VerificationStatus`)

| Status | Verification Rank | Category | Definition |
| :--- | :---: | :--- | :--- |
| **`FORMALLY_PROVED`** | 10 | Deductive Proof | Machine-checked proof verified by Lean 4 kernel with zero `sorry` axioms. |
| **`SYMBOLIC_CHECKED`** | 5 | Computer Algebra | Algebraically verified to zero or proven by symbolic calculus in SymPy. |
| **`NUMERICALLY_CHECKED`** | 4 | Computation | Trajectory verified via numerical ODE integration (e.g. RK45) within bound $\epsilon$. |
| **`STATISTICALLY_CHECKED`** | 4 | Empirical / Data | Parameter fit supported by regression ($R^2$, reduced $\chi^2$) against data. |
| **`DIMENSIONALLY_CHECKED`** | 3 | Physical Constraint | Homogeneity of physical units verified across base SI dimensions. |
| **`STRUCTURALLY_VALID`** | 2 | Graph Topology | Derivation graph is verified acyclic (DAG) and structurally coherent. |
| **`CONDITIONAL`** | 2 | Dependency Blocked | Valid step, but depends on an unproven, inactive, or dropped physical assumption. |
| **`PARSED`** | 1 | Syntax | Syntactically valid and parsed into canonical IR AST. |
| **`AI_PROPOSED`** | 1 | Unverified Proposal | Proposed by an AI model or external heuristic. **Not verified**. |
| **`UNVERIFIED`** | 0 | Baseline | Untested step with no verification backend run. |
| **`NOT_APPLICABLE`** | 0 | N/A | Definition or axiom where automated verification is not applicable. |
| **`TIMEOUT`** | -1 | Resource Exhaustion | Verification backend exceeded time or memory limits. |
| **`FAILED`** | -1 | Contradiction / Failure | Backend rejected step (e.g. algebraic contradiction or Lean syntax/type error). |
| **`DISPROVED`** | -2 | Counterexample | Explicit mathematical counterexample found. Step is mathematically false. |

---

## 2. The Role of `AI_PROPOSED`

In Automate 0.2, AI agents cannot self-certify:
- When an AI agent submits a proposal via `automate.proposal.v1`, the resulting graph node and edge enter the system tagged strictly as `VerificationStatus.AI_PROPOSED`.
- The `is_verified` property evaluates to `False` for `AI_PROPOSED`.
- Only when an independent backend (SymPy, Lean 4, SciPy, DimensionChecker) processes the step does the status upgrade to `SYMBOLIC_CHECKED`, `FORMALLY_PROVED`, etc.
- If the verification fails, the step transitions to `FAILED`.

---

## 3. Transitive Assumption Dependency Tracking

Every physical derivation is contingent upon idealizations and physical regimes (e.g. small angles $\theta \ll 1$, non-relativistic velocities $v \ll c$, mass $m > 0$, fixed boundary endpoints).

### 3.1 Transitive Inheritance
Automate computes the exact transitive closure of all assumptions supporting any node $N$:
$$\text{Assumptions}(N) = \text{DeclaredAssumptions}(N) \cup \bigcup_{P \in \text{Parents}(N)} \text{Assumptions}(P)$$

### 3.2 Assumption Removal Simulation
Automate can simulate the consequence of dropping an assumption:
```bash
automate query-assumptions examples/harmonic_oscillator.yaml --drop asm_pos_mass
```
The graph engine:
1. Identifies all nodes that depend directly or transitively on `asm_pos_mass`.
2. Computes the survival ratio $\frac{|\text{Surviving Nodes}|}{|\text{Total Nodes}|}$.
3. Identifies invalidated edges and downstream nodes rendered `CONDITIONAL` or unproven.

---

## 4. Multi-Backend Evidence Model (`VerificationEvidence`)

Evidence is stored as structured metadata on each `DerivationEdge`:

```json
{
  "status": "SYMBOLIC_CHECKED",
  "passed": true,
  "checker": "SymPyChecker",
  "checker_version": "1.13.3",
  "execution_time_ms": 3.82,
  "details": {
    "rule": "solve_harmonic_oscillator",
    "ode_residual": "0",
    "verified_algebraically": true
  },
  "reproducibility": {
    "source_hash": "d41d8cd98f00b204e9800998ecf8427e",
    "toolchain": "Python 3.13 / SymPy 1.13.3",
    "deterministic": true
  },
  "graph_id": "harmonic_oscillator",
  "edge_id": "edge_sol"
}
```

This guarantees that any external verifier or auditor can inspect exactly how, when, and under what tolerances each derivation step was verified.
