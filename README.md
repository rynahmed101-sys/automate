# Automate

> **Local-First, Machine-Checkable Formal Physics Derivation Engine**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Lean 4: v4.34.1](https://img.shields.io/badge/Lean%204-v4.34.1-purple.svg)](https://lean-lang.org/)
[![SymPy: Verified](https://img.shields.io/badge/SymPy-1.14-green.svg)](https://www.sympy.org/)
[![JSON Schema: v0.1](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-orange.svg)](schemas/automate-ir-v0.1.json)
[![Tests: 24 Passed](https://img.shields.io/badge/Tests-24%20passed-brightgreen.svg)](tests/)

Automate is an open-source, local-first computational framework that unifies:
1. **Symbolic Mathematics & Calculus** (SymPy)
2. **Formal Interactive Theorem Proving** (Lean 4)
3. **High-Precision Numerical Simulation** (NumPy, SciPy, mpmath)
4. **Statistical Inference & Uncertainty Quantification** (SciPy)
5. **Physical Dimensional Consistency** (SI Base Dimensions)
6. **Hierarchical, Machine-Auditable Derivation Graphs** with First-Class Assumption Tracking.

Automate treats physics derivations not as static linear LaTeX documents, but as **directed acyclic derivation graphs (DAGs)** where every single transformation step is machine-checkable, assumptions are explicitly propagated, and high-level steps can be losslessly expanded into formal micro-proof certificates.

---

## Architecture & Ecosystem Strategy

For detailed architectural analysis and open-source ecosystem mappings, see:
* [Architecture Audit](docs/ARCHITECTURE_AUDIT.md): Comprehensive evaluation of current components, representation gaps, and verification guarantees.
* [Ecosystem Survey & Strategy](docs/ECOSYSTEM.md): Pragmatic integration roadmap across Lean 4, Mathlib, Physlib, Physics Derivation Graph, SymPy, SciPy, and Z3.

```
Human / AI
    ↓
Physics Intermediate Representation (AST + Assumptions + Dimensions)
    ↓
Derivation Graph (DAG)
    ↓
Specialized Verification Backends:
 ├── Dimensional Analysis  → Base SI dimensions [M, L, T, I, Theta, N, J]
 ├── Computer Algebra      → SymPy (Euler-Lagrange, ODE solution zero-testing)
 ├── Formal Theorem Prover → Lean 4 (on-shell algebraic invariance & identities)
 ├── Numerical Simulation  → SciPy (RK45 IVP integration, symplectic drift)
 └── Statistical Engine    → SciPy (Non-linear regression, chi2 residuals)
    ↓
Verifiable Certificate Package (certificate.json, obligations.json, evidence.json)
```

---

## Canonical Physics Milestone: 1D Simple Harmonic Oscillator

```
    [ Lagrangian: L = 1/2*m*x_dot^2 - 1/2*k*x^2 ]
                         │
                         │ Euler-Lagrange Rule (Hamilton's Action Principle)
                         │ Checker: SymPy + Dimension
                         ▼
        [ Equation of Motion: m*x_ddot + k*x = 0 ]
           ├───┬────────────────────────────────────────┐
           │   │                                        │
           │   │ Noether's Theorem                      │ Runge-Kutta IVP
           │   │ Checker: Lean 4                        │ Checker: SciPy (RK45)
           │   ▼                                        ▼
           │ [ Conserved Energy: E = const ]    [ Numerical Trajectory: x(t) ]
           │
           │ Linear ODE Solution
           │ Checker: SymPy
           ▼
    [ Analytic Trajectory: x(t) = A*cos(omega*t + phi) ]
           │
           │ Empirical Non-Linear Regression
           │ Checker: SciPy (Chi-Square)
           ▼
    [ Observed Parameter Estimate: omega = 2.000 rad/s ]
```

### Verification Status Taxonomy & Honest Semantics
Automate strictly distinguishes between levels of mathematical certainty:
* `FORMALLY_PROVED`: Verified through a sound interactive theorem prover kernel (Lean 4).
* `SYMBOLIC_CHECKED`: Verified via computer algebra zero-testing and calculus (SymPy).
* `NUMERICALLY_CHECKED`: Tested via numerical ODE integration and energy drift bounds (SciPy).
* `STATISTICALLY_CHECKED`: Validated against empirical observations with parameter estimation and $\chi^2$ residuals (SciPy).
* `DIMENSIONALLY_CHECKED`: Homogeneous physical dimensions confirmed across all terms.
* `STRUCTURALLY_VALID`: Acyclic DAG topology and node identifier integrity confirmed.
* `CONDITIONAL`: Dependent on active or unproven physical assumptions/approximations.
* `PARSED`: Validated syntax and loaded into canonical IR.
* `UNVERIFIED`: Not yet checked by any verification backend.
* `FAILED`: Contradiction detected, obligation violated, or checker raised an error.
* `DISPROVED`: Mathematically disproved or counterexample discovered.

> **CRITICAL SEMANTIC GUARANTEE**: Never represent "AI believes this is correct" as PROVED. Lean 4 verifies discrete algebraic and on-shell invariance identities without external axioms; SymPy verifies continuous differential variations; SciPy checks empirical and numerical bounds. Each backend is explicitly identified in every derivation certificate.

---

## Assumptions as First-Class Objects
In Automate, assumptions ($m > 0$, $k > 0$, $x(t) \in C^2(\mathbb{R})$, vanishing boundary terms) are explicitly tracked throughout the DAG.
You can query:
* *"Which conclusions depend on assumption A?"*
* *"What survives if assumption A is removed?"*
* *"Which nodes require the predicate 'positivity'?"*

Dropping an assumption automatically computes the transitive dependency closure, flagging all downstream nodes as invalidated or conditional.

---

## Quickstart

### 1. Installation
```powershell
# Clone the repository
git clone https://github.com/rynahmed101-sys/automate.git
cd automate

# Setup Python virtual environment
python -m virtualenv .venv
.venv\Scripts\pip.exe install -e .

# (Optional) Install Lean 4 toolchain
elan toolchain install stable
```

### 2. Run the End-to-End Physics Demonstration
One single command executes the entire verification pipeline for the 1D Harmonic Oscillator:
```powershell
.venv\Scripts\automate.exe demo
```

This will:
1. Parse `examples/harmonic_oscillator.yaml` into canonical Intermediate Representation (IR).
2. Validate DAG acyclicity and topological ordering.
3. Verify dimensional consistency across all terms ($[L] = \text{Joules}$, $[F] = \text{Newtons}$).
4. Symbolically verify Euler-Lagrange equations of motion and ODE general solution with SymPy.
5. Formally compile and verify the energy conservation theorem in Lean 4.
6. Execute Runge-Kutta 4(5) numerical simulation and check energy conservation drift ($\Delta E/E_0 < 10^{-6}$).
7. Perform empirical non-linear parameter estimation and compute reduced $\chi^2$ and 95% confidence intervals.
8. Perform assumption sensitivity analysis (simulating removal of $m > 0$).
9. Generate standalone interactive HTML graph (`output/harmonic_oscillator.html`).
10. Export self-contained, machine-auditable verification certificate package (`output/certificates/`).

---

## CLI Reference

```powershell
# Run the canonical end-to-end physics demo
automate demo

# Parse a declarative theory file into a JSON derivation graph
automate parse examples/harmonic_oscillator.yaml -o graph.json

# Run symbolic and dimensional checks
automate check graph.json

# Execute Lean 4 formal prover on proof obligations
automate prove graph.json

# Run numerical ODE integration (SciPy RK45)
automate simulate graph.json

# Run empirical parameter estimation & residual goodness-of-fit
automate stats graph.json

# Inspect assumption dependencies or simulate dropping an assumption
automate query-assumptions graph.json --drop asm_pos_mass

# Losslessly expand a high-level step into micro-steps
automate expand graph.json --edge edge_euler_lagrange

# Generate standalone interactive HTML graph visualizer
automate visualize graph.json -o graph.html

# Print formatted verification matrix
automate report graph.json

# Export self-contained verifiable certificate package
automate export-certificate graph.json -o certificates/
```

---

## Testing & Verification

Automate includes an automated test suite covering AST operations, dimensional arithmetic, assumption inheritance, sensitivity simulation, cycle detection, lossless certificate expansion, failure propagation, JSON schema validation, Lean 4 toolchain execution, SymPy calculus, SciPy ODE integration, and non-linear parameter inference:

```powershell
.venv\Scripts\pytest.exe tests/ -v
# 24 passed in ~15s
```

---

## License
Apache License 2.0. See [LICENSE](LICENSE) for details.
