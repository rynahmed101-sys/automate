# Automate

> **Local-First, Machine-Checkable Formal Physics Derivation Engine**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Lean 4: v4.34.1](https://img.shields.io/badge/Lean%204-v4.34.1-purple.svg)](https://lean-lang.org/)
[![SymPy: Verified](https://img.shields.io/badge/SymPy-1.14-green.svg)](https://www.sympy.org/)

Automate is an open-source, local-first computational framework that unifies:
1. **Symbolic Mathematics & Calculus** (SymPy)
2. **Formal Interactive Theorem Proving** (Lean 4)
3. **High-Precision Numerical Simulation** (NumPy, SciPy, mpmath)
4. **Statistical Inference & Uncertainty Quantification** (SciPy)
5. **Physical Dimensional Consistency** (SI Base Dimensions)
6. **Hierarchical, Machine-Auditable Derivation Graphs** with First-Class Assumption Tracking.

Automate treats physics derivations not as static linear LaTeX documents, but as **directed acyclic derivation graphs (DAGs)** where every single transformation step is machine-checkable, assumptions are explicitly propagated, and high-level steps can be losslessly expanded into formal micro-proof certificates.

---

## Core Principle: Derivation Graphs

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

### Verification Status Taxonomy
Automate strictly distinguishes between levels of mathematical certainty:
* `FORMALLY_PROVED`: Verified through a sound interactive theorem prover (Lean 4).
* `SYMBOLIC_CHECKED`: Verified via computer algebra zero-testing and calculus (SymPy).
* `NUMERICALLY_CHECKED`: Tested via numerical ODE integration and energy drift bounds (SciPy).
* `STATISTICALLY_CHECKED`: Validated against empirical observations with parameter estimation and $\chi^2$ residuals (SciPy).
* `CONDITIONAL`: Dependent on active or unproven physical assumptions/approximations.
* `PARSED`: Validated syntax and loaded into canonical IR.
* `UNVERIFIED`: Not yet checked by any verification backend.
* `FAILED`: Contradiction detected or proof obligation failed.

> **Never represent "AI believes this is correct" as PROVED.**

---

## Assumptions as First-Class Objects
In Automate, assumptions ($m > 0$, $k > 0$, $x(t) \in C^2(\mathbb{R})$, vanishing boundary terms) are explicitly tracked throughout the DAG.
You can query:
* *"Which conclusions depend on assumption A?"*
* *"What survives if assumption A is removed?"*

Dropping an assumption automatically flags all downstream nodes as `CONDITIONAL` or invalidated.

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
10. Output machine-readable JSON execution log (`output/verification_report.json`).

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
```

---

## License
Apache License 2.0. See [LICENSE](LICENSE) for details.
