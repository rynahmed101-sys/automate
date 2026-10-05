# Automate AI: Autonomous Agent Operations Manual

> **Governing Philosophy**: *"AI proposes. Automate represents. Verification backends check. Evidence determines status."*

This document is the official guide for AI coding assistants, autonomous agents, and language models interacting directly with the `automate` repository.

Automate is designed from first principles to be **100% locally self-reliant**. You do **not** need an API key, an active internet connection, or external cloud accounts to run, test, propose, or verify derivations.

---

## 1. Zero-Setup Agent Discovery

When an AI agent clones this repository, the first action should be discovering the active environment and backend capabilities via the machine-readable JSON interface:

```bash
automate capabilities --json
```

### Example Machine Response:
```json
{
  "schema_version": "0.2.0",
  "ir": true,
  "tensors": true,
  "actions": true,
  "differential_geometry": true,
  "symbolic": true,
  "dimensions": true,
  "numerical": true,
  "statistics": true,
  "lean4": true,
  "lean4_version": "Lean (version 4.15.0)",
  "ai": true,
  "providers": {
    "mock": true,
    "openai": false,
    "local": false
  }
}
```

The response indicates which backends are active. If Lean 4 is installed locally (e.g. via `elan`), formal theorem proving is enabled. If not, Automate falls back cleanly to computer algebra (SymPy), numerical simulation (SciPy RK45), and dimensional homogeneity checks.

---

## 1.5 Machine-Agent Capability Contract

The authoritative machine-agent manifest is available directly from the CLI:

```bash
automate schema --name agent
```

The manifest is versioned as `automate.agent.v1`. It describes the complete current machine-facing command surface, supported mathematics and physics capability families, all registered transformation rules, optional provider/back-end availability, verification statuses, trust rules, and certificate artifacts.

Agents should run `automate capabilities --json` first to discover runtime availability, then retrieve the stable contract with `automate schema --name agent`. The intended workflow is:

`discover → context → construct proposal → validate → dry-run → apply → inspect evidence → export certificate`

This is an interface over the existing Automate system, not a second implementation. Agents should rely on the declared JSON contracts and status semantics rather than importing private Python implementation details.

## 2. Extracting Controlled Mathematical Context

To propose mathematically sound derivation steps, an agent needs to know the existing equations, variables, active physical assumptions, and approved transformation rules. 

Run:
```bash
automate context examples/harmonic_oscillator.yaml --json
```

### Security & Sanitization Invariant:
The context generator (`automate/ai/context.py`) produces an `automate.context.v1` payload. It **strictly isolates mathematical physics state** from machine-specific data:
- No file system paths or directory trees
- No environment variables, tokens, or credentials
- Deterministic `graph_hash` (SHA-256 computed strictly over mathematical ASTs and assumptions)

---

## 3. Creating an Untrusted Proposal (`automate.proposal.v1`)

Agents propose new derivation steps by emitting structured JSON conforming to `automate.proposal.v1`.

### Proposal Template:
```json
{
  "schema_version": "automate.proposal.v1",
  "proposal_id": "prop_agent_001",
  "proposal_type": "derivation",
  "input_nodes": ["node_eom"],
  "output_nodes": [
    {
      "id": "node_harmonic_sol",
      "expression": "x(t) = A * cos(omega * t + phi)",
      "dimension": "L",
      "latex": "x(t) = A\\cos(\\omega t + \\phi)",
      "node_kind": "equation",
      "domain": "classical_mechanics"
    }
  ],
  "rule": "solve_harmonic_oscillator",
  "justification": "General solution to 2nd-order linear homogeneous ordinary differential equation with constant coefficients",
  "side_conditions": ["asm_pos_mass", "asm_pos_k"],
  "target_checker": "sympy",
  "parameters": {
    "omega": "sqrt(k/m)"
  },
  "origin": {
    "type": "ai",
    "provider": "autonomous_agent",
    "model": "agent-v1"
  }
}
```

### Mandatory Rules for Proposals:
1. **Never Self-Assign Status**: A proposal must never set `status` to `FORMALLY_PROVED` or `SYMBOLIC_CHECKED`. Any proposal attempting to do so is immediately rejected by `automate/ai/validation.py`.
2. **Reference Valid Inputs**: `input_nodes` must exist in the derivation graph.
3. **Use Approved Rules**: `rule` must exist in Automate's `RuleRegistry` (`automate/theory/rules.py`).
4. **Declare Side Conditions**: If the transformation relies on mass being positive or endpoints being fixed, explicitly list the assumption IDs in `side_conditions`.

---

## 4. Validating and Testing Proposals (Dry-Run Mode)

Before applying a proposal to a canonical graph, test it without side effects:

### Step 4A: Pre-flight Security & Schema Validation
```bash
automate validate my_proposal.json --theory examples/harmonic_oscillator.yaml --json
```

Automate scans the payload against dangerous patterns (`eval`, `exec`, shell metacharacters, path traversal, injection attacks) and validates dependency nodes.

### Step 4B: Execution Dry-Run
```bash
automate propose examples/harmonic_oscillator.yaml --proposal my_proposal.json --dry-run --json
```

In dry-run mode:
- The graph is cloned in memory.
- A candidate edge is injected with `status: "AI_PROPOSED"`.
- Verification obligations are synthesized from the `RuleRegistry`.
- Backends execute the checks.
- Dimensional homogeneity is validated.
- The canonical graph remains completely untouched.

---

## 5. Applying Proposals and Generating Evidence

To commit the verified step to the derivation graph:

```bash
automate propose examples/harmonic_oscillator.yaml --proposal my_proposal.json --output updated_graph.json --json
```

If backend verification passes:
1. The edge status transitions from `AI_PROPOSED` to `SYMBOLIC_CHECKED` (or `FORMALLY_PROVED` if Lean 4 succeeded).
2. The verification report is attached to the edge.
3. A lossless execution certificate is synthesized.
4. The updated graph is saved to `updated_graph.json`.

---

## 6. Running Autonomous Bounded Research Loops

Agents can execute multi-step research loops where candidates are sequentially proposed, validated, verified, and chained:

```bash
automate research examples/harmonic_oscillator.yaml --provider mock --max-steps 3 --output-dir research_run --json
```

The resulting directory contains:
- `research_graph.json`: The augmented derivation graph.
- `research_trace.json`: Step-by-step history of proposals, verification outcomes, and runtimes.

---

## 7. Machine-Auditable Verification Certificate Packages

To generate a complete, tamper-evident certificate package:

```python
from automate.theory.parser import parse_theory_file

graph = parse_theory_file("examples/harmonic_oscillator.yaml")
files = graph.export_certificate_package("dist/cert_package")
```

The package produces 7 decoupled artifacts with a root `manifest.json` containing SHA-256 hashes:
1. `certificate.json`: Global status summary, verification rate, node/edge counts.
2. `assumptions.json`: Declared assumptions and per-node transitive dependencies.
3. `obligations.json`: Formal obligations synthesized per edge.
4. `evidence.json`: Backend verification reports, numerical residuals, Lean proof scripts.
5. `subgraph_expansion.json`: Micro-step expansions of composite derivations.
6. `provenance.json`: Origin metadata, timestamps, compiler versions, graph hashes.
7. `manifest.json`: Cryptographic SHA-256 checksums of all package artifacts.
