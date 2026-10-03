# Verification Standards & Soundness in Automate

Automate adheres to a philosophy of strict verification hygiene. We reject the paradigm where an AI model claims a theory is "true" without machine-auditable certificates.

---

## 1. Multiple Verification Authorities

Different aspects of mathematical physics require different verification disciplines:

| Domain | Authority | Verification Criteria | Status Assigned |
| :--- | :--- | :--- | :--- |
| **Algebra & Calculus** | SymPy | Direct symbolic differentiation, zero-testing $(A - B == 0)$ | `SYMBOLIC_CHECKED` |
| **Formal Theorems** | Lean 4 | Type-theoretic proof checking with Lean 4 kernel | `FORMALLY_PROVED` |
| **Differential Equations** | SciPy | Numerical IVP integration, energy conservation drift $\Delta E / E_0 < 10^{-4}$ | `NUMERICALLY_CHECKED` |
| **Empirical Validation** | SciPy | Non-linear regression, $R^2 > 0.90$, reduced $\chi^2 \in [0.5, 2.0]$ | `STATISTICALLY_CHECKED` |
| **Dimensional Analysis** | Automate IR | Base SI dimension algebra homogeneity $[M]^a [L]^b [T]^c$ | Checked alongside rules |

---

## 2. Integrity Rules

1. **No Silent Assumption Drops**:
   If a theorem depends on $m > 0$ or vanishing boundary terms, that assumption remains bound to all downstream conclusions. Dropping the assumption invalidates the downstream subgraph.
2. **Lean Proof Failures are Legitimate**:
   If Lean 4 returns a non-zero exit code or compilation error, the status is set to `FAILED`. It is never recorded as "probably correct".
3. **Statistics Do Not Prove Mathematics**:
   Fitting noisy experimental data validates empirical agreement; it never upgrades a mathematical hypothesis to `FORMALLY_PROVED`.
4. **Sandboxed Subprocess Execution**:
   Lean code and numerical scripts are executed in isolated temporary scratch directories with execution timeouts to prevent runaway processes.
