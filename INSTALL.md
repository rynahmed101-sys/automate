# Installation & Environment Guide: Automate

This document details how to install and configure **Automate** in a local, self-reliant environment without external cloud APIs.

## Prerequisites

1. **Operating System**: Windows 10/11, Linux (Ubuntu 22.04+), or macOS (12+).
2. **Python**: Python 3.10, 3.11, 3.12, or 3.13.
3. **Git**: Git 2.30+.
4. **Lean 4** (Recommended for formal proofs): Installed via `elan`.

---

## 1. Local Python Setup

Create a clean virtual environment and install Automate in editable mode:

```powershell
# Windows (PowerShell)
cd F:\Projects\automate
python -m virtualenv .venv
& ".\.venv\Scripts\pip.exe" install --cache-dir "F:\pip-cache" -e .
```

On Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Dependencies
Automate relies strictly on mature open-source components:
* `sympy>=1.12`: Symbolic computer algebra and calculus.
* `numpy>=1.24`: Fast numerical array and matrix computation.
* `scipy>=1.10`: Differential equation integration (`solve_ivp`), optimization, and statistical testing.
* `mpmath>=1.3`: Arbitrary precision floating-point arithmetic.
* `pydantic>=2.0`: Strongly-typed schema validation and JSON serialization.
* `pyyaml>=6.0`: Declarative YAML theory parsing.
* `click>=8.1`: Command line interface.
* `rich>=13.0`: Terminal formatting and tables.
* `matplotlib>=3.7`: Plotting and trajectory inspection.

---

## 2. Lean 4 Formal Verification Backend Setup

Lean 4 is used to check formal proof obligations.

### Windows (Elan)
1. Download `elan-init.exe` from GitHub releases:
   ```powershell
   curl.exe -sL -o F:\Temp\elan.zip https://github.com/leanprover/elan/releases/download/v4.2.4/elan-x86_64-pc-windows-msvc.zip
   Expand-Archive -Path F:\Temp\elan.zip -DestinationPath F:\elan_bootstrap -Force
   $env:ELAN_HOME = "F:\elan"
   F:\elan_bootstrap\elan-init.exe -y --default-toolchain stable
   ```
2. Verify Lean installation:
   ```powershell
   & "F:\elan\bin\lean.exe" --version
   # Expected output: Lean (version 4.x.x, ...)
   ```

### Linux / macOS
```bash
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y --default-toolchain stable
source $HOME/.elan/env
lean --version
```

---

## 3. Verification of Installation

Run the complete test suite:
```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v
```

Run the end-to-end physics demo:
```powershell
& ".\.venv\Scripts\automate.exe" demo
```
