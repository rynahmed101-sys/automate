# Automate

> **Local-First, Machine-Checkable Formal Physics Derivation Engine**
> Version 0.2.0 • Canonical Mathematical Semantics • Universal AI Interface • Offline Verification

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Lean 4: v4.15+](https://img.shields.io/badge/Lean%204-v4.15%2B-purple.svg)](https://lean-lang.org/)
[![SymPy: Verified](https://img.shields.io/badge/SymPy-1.13%2B-green.svg)](https://www.sympy.org/)
[![JSON Schema: v0.2](https://img.shields.io/badge/JSON%20Schema-v0.2-orange.svg)](schemas/automate-ir-v0.1.json)
[![Tests: 48 Passed](https://img.shields.io/badge/Tests-48%20passed-brightgreen.svg)](tests/)

Automate is an open-source, local-first computational framework that unifies:
1. **Canonical Mathematical Physics Semantics**: Typed ASTs, relativistic tensors, Einstein summation index algebra, spacetime manifolds, curvature tensors, and action functionals.
2. **Universal AI Agent Subsystem**: Zero-trust AI proposal validation, offline mock provider, local LLM/OpenAI adapters, and controlled mathematical context generation.
3. **Symbolic Mathematics & Calculus**: Computer algebra zero-testing, Euler-Lagrange equations, and ODE solutions (SymPy).
4. **Formal Interactive Theorem Proving**: Machine-checked mathematical physics lemmas and invariance theorems (Lean 4).
5. **High-Precision Numerical Simulation**: Runge-Kutta 4(5) initial value problem integration and energy conservation drift tracking (SciPy).
6. **Statistical Inference & Uncertainty Quantification**: Non-linear parameter estimation, covariance matrices, and $\chi^2$ goodness-of-fit (SciPy).
7. **Physical Dimensional Homogeneity**: Automated SI base dimension consistency verification ($[M, L, T, I, \Theta, N, J]$).
8. **Machine-Auditable Certificate Packages**: Tamper-evident verification exports with cryptographic SHA-256 manifests.

Automate treats physics derivations not as static linear LaTeX documents, but as **directed acyclic derivation graphs (DAGs)** where every single transformation step is machine-checkable, assumptions are explicitly propagated, and high-level steps can be losslessly expanded into formal micro-proof certificates.

---

## 🌱 Project Workspace

Automate is developed as a verification-first engineering workspace: small steps, explicit evidence, and honest status.

- **[Project Operations](docs/PROJECT_OPERATIONS.md)**: working model, roadmap structure, and verification vocabulary.
- **GitHub Issues**: bounded bugs, research questions, and implementation tasks.
- **GitHub Projects**: visual planning and progress tracking when enabled for the repository.
- **GitHub Actions**: authoritative automated verification.
- **Pull Requests**: reviewable implementation boundaries.
- **Wiki / Discussions**: long-form architecture and design conversations when supported by the repository plan.

Current principle: **build carefully, verify honestly, keep the next step visible.** 🌤️

> **Everything may be questioned. Nothing is automatically believed. Nothing is automatically dismissed merely for being unconventional.**
>
> See **[Automate's One Giant Truth](docs/ONE_GIANT_TRUTH.md)** for the project's foundational stance on inquiry, verification, established knowledge, and unconventional ideas.

## Mathematics & Physics Capability Roadmap

The active expansion program is capability-first: Automate is being extended from its current symbolic, mechanics, tensor/geometry, and numerical foundations into linear algebra, vector calculus, electromagnetism, broader differential equations, PDEs, relativity, thermodynamics, quantum mechanics, and advanced mathematical physics.

See **[Development Stages & Capability Ledger](docs/PROJECT_PHASE_LEDGER.md)** for the single dependency-ordered mathematical/physics roadmap, development-depth rules, current status, and next capability. `docs/MATH_PHYSICS_ROADMAP.md` is retained only as a compatibility pointer. The project deliberately favors coherent capability PRs and squash merges over thousands of micro-commits.

## Direct AI Coding Agent Interface

Automate 0.2 is purpose-built for direct interaction with autonomous AI coding agents without requiring internet access, cloud accounts, or proprietary APIs.

* **[AI Agent Operations Manual](AUTOMATE_AI.md)**: Complete guide for AI coding assistants to clone, inspect, propose, and verify.
* **[AI Integration Architecture](AI_INTEGRATION.md)**: Zero-trust security boundary, provider adapters, and candidate ingestion pipelines.
* **[Schema Catalog & Formats](SCHEMAS.md)**: Specifications for IR, AI context, proposal formats, and certificate packages.
* **[Security Architecture & Threat Model](SECURITY.md)**: Static pattern interception, sandboxing, and denial-of-service bounds.
* **[Canonical IR Specification](docs/IR_SPECIFICATION.md)**: Typed expression ASTs, tensor index contraction algebra, and differential geometry primitives.
* **[Verification Model & Status Taxonomy](docs/VERIFICATION_MODEL.md)**: Honest multidimensional verification semantics without scalar percentage scores.

---

## Core System Architecture

```
Human / AI Coding Agent
    ↓  (automate context <theory> --json)
Controlled Mathematical Context (automate.context.v1)
    ↓  (automate.proposal.v1)
Security & Schema Validator (automate/ai/validation.py)
    ↓  (AI_PROPOSED status)
Derivation Graph (DAG) + Rule Registry Obligations
    ↓
Specialized Verification Backends:
 ├── Dimensional Analysis  → Base SI dimensions [M, L, T, I, Theta, N, J]
 ├── Computer Algebra      → SymPy (Euler-Lagrange, ODE solution zero-testing)
 ├── Formal Theorem Prover → Lean 4 (on-shell algebraic invariance & identities)
 ├── Numerical Simulation  → SciPy (RK45 IVP integration, symplectic drift)
 └── Statistical Engine    → SciPy (Non-linear regression, chi2 residuals)
    ↓
Cryptographically Hashed Certificate Package (manifest.json with SHA-256)
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
* `AI_PROPOSED`: Hypothesis proposed by an AI agent; strictly unverified until backends evaluate it.
* `PARSED`: Validated syntax and loaded into canonical IR AST.
* `UNVERIFIED`: Not yet checked by any verification backend.
* `FAILED`: Contradiction detected, obligation violated, or checker raised an error.
* `DISPROVED`: Mathematically disproved or counterexample discovered.

> **CRITICAL SEMANTIC GUARANTEE**: Never represent "AI believes this is correct" as PROVED. Lean 4 verifies discrete algebraic and on-shell invariance identities without external axioms; SymPy verifies continuous differential variations; SciPy checks empirical and numerical bounds. Each backend is explicitly recorded in every derivation certificate.

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

---

## CLI Reference

### Machine-Readable Agent Commands (`--json`)
```powershell
# Discover available verification backends, IR features, and AI providers
automate capabilities --json

# Extract sanitized mathematical context for an AI agent
automate context examples/harmonic_oscillator.yaml --json

# Validate an untrusted proposal against security rules and schema
automate validate proposal.json --theory examples/harmonic_oscillator.yaml --json

# Dry-run or execute an AI derivation step
automate propose examples/harmonic_oscillator.yaml --request "Solve equation of motion" --dry-run --json

# Run a bounded autonomous research loop
automate research examples/harmonic_oscillator.yaml --provider mock --max-steps 3 --json

# Dump canonical JSON schemas
automate schema --name ir
```

### Human-Readable CLI Commands
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

# Export self-contained verifiable certificate package with SHA-256 manifest
automate export-certificate graph.json -o certificates/
```

---

## Testing & Quality Assurance

Automate includes a comprehensive test suite covering typed AST serialization, tensor Einstein summation, field theory actions, differential geometry, AI security validation, mock providers, CLI JSON commands, Lean 4 toolchain execution, SymPy calculus, SciPy ODE integration, and non-linear parameter inference:

```powershell
.venv\Scripts\pytest.exe -v
# 48 passed in ~20s
```

---

## License
Apache License 2.0. See [LICENSE](LICENSE) for details.
