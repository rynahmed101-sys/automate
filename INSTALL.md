# Installation & Environment Guide: Automate

Install **Automate** locally without an external cloud AI provider. Package
metadata in `pyproject.toml` is authoritative for dependencies and the
`automate` command entry point.

## Prerequisites

1. **Operating System**: Windows 10/11, Linux (Ubuntu 22.04+), or macOS (12+).
2. **Python**: Python 3.10, 3.11, 3.12, or 3.13.
3. **Git**: Git 2.30+.
4. **Lean 4** (optional): Required only for the local Lean proof-checking
   backend; it is not a dependency of the calculator API.

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

The runtime dependencies declared in `pyproject.toml` include SymPy, NumPy,
SciPy, mpmath, Pydantic, PyYAML, Click, Rich, Matplotlib, jsonschema,
EinsteinPy, Pint, and lmfit. Install from the project metadata rather than
maintaining a separate dependency list here:

```sh
python -m pip install .
```

For local tests, install the development extra with
`python -m pip install -e ".[dev]"`.

---

## 2. Optional Lean 4 Backend Setup

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

```sh
pytest -q
```

Check the calculator installation:

```sh
automate capabilities --json
automate calculate --operation differentiate --expression "x**2" --variable x --json
```

The graph-based end-to-end demo remains available through `automate demo`.
