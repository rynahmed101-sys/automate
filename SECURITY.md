# Automate Security Architecture & Threat Model

Automate is designed to interact safely with untrusted inputs, including machine-generated proposals from Large Language Models and external contributors.

---

## 1. Threat Model & Security Invariants

| Threat / Risk | Mitigating Invariant | Enforcement Point |
| :--- | :--- | :--- |
| **Arbitrary Code Execution** | `eval()` and `exec()` are **strictly forbidden**. Proposals are parsed exclusively as declarative JSON data into Pydantic models. | `automate/ai/validation.py` |
| **Shell & OS Command Injection** | Subprocess invocations do not use `shell=True`. Arguments are passed as sanitized argument lists. Input strings are scanned for shell metacharacters and subprocess calls. | `automate/backend/lean_backend.py`, `automate/ai/validation.py` |
| **Path Traversal & File Overwrite** | Candidate nodes and proposals cannot specify file paths or relative directory references (`../`, `..\`). | `automate/ai/validation.py` |
| **Credential & Secret Leakage** | The AI context builder (`build_ai_context`) operates strictly on mathematical ASTs and assumptions. It never reads or serializes environment variables, API keys, or host file paths. | `automate/ai/context.py` |
| **Self-Assigned Verification Forgery** | An agent cannot claim a proposition is verified. Any proposal attempting to set `status` to `FORMALLY_PROVED` or `SYMBOLIC_CHECKED` is rejected before graph ingestion. | `automate/ai/validation.py` |
| **Denial of Service (DoS) via Giant Payload** | AI proposals are bounded to a maximum payload size of 64 KB. | `automate/ai/validation.py` |
| **Computational Resource Exhaustion** | Verification backends (Lean, SymPy) execute with bounded timeouts. Graph acyclicity is enforced via Kahn's algorithm before topological evaluation. | `automate/backend/base.py`, `automate/core/graph.py` |

---

## 2. In-Depth Defensive Measures

### 2.1 Static Pattern Interception
Before parsing JSON into data models, `validate_ai_proposal` scans raw strings using pre-compiled regular expressions for dangerous constructs:
- Python execution: `eval\s*\(`, `exec\s*\(`, `__import__`, `subprocess`, `os\.system`, `shutil`
- File operations: `open\s*\(`, `read_bytes`, `write_bytes`, `unlink`, `remove`
- Shell binaries and scripts: `powershell`, `/bin/sh`, `/bin/bash`, `cmd\.exe`
- Shell metacharacters: backticks (`` `...` ``), subshell expansions (`$(...)`), command chaining (`; rm`, `; del`)
- Path traversal: `../`, `..\`
- Token patterns: `OPENAI_API_KEY`, `ghp_`, `apiKey`

### 2.2 Strict Schema Conformance
Automate leverages typed Pydantic models with `model_config = ConfigDict(extra='forbid')` or strict field validation. Unknown fields or mismatched types produce immediate validation errors, preventing prototype pollution or injection of unauthorized parameters.

### 2.3 Lean 4 Subprocess Isolation
The Lean backend:
- Never executes user-supplied binary executables.
- Invokes the discovered `lean` compiler with explicit arguments: `[str(lean_bin), str(lean_file)]`.
- Runs inside a controlled temporary directory.
- Captures `stdout` and `stderr` with a 30-second timeout.
- Records the full source hash and generated code for auditability.

### 2.4 Controlled Context Sanitization
When an agent calls `automate context <file> --json`:
- The mathematical state is serialized without local host path information.
- A deterministic `graph_hash` is computed from the mathematical ASTs, node names, equations, and active assumptions. Machine-specific timestamps and host file locations are deliberately excluded.

---

## 3. Reporting Security Issues

To report a vulnerability or flaw in Automate's verification or security boundaries, please open a GitHub security advisory or contact the maintainers directly.
