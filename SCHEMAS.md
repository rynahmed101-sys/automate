# Automate Schema Specifications

Automate uses explicit, versioned JSON schemas for all canonical data representations, agent exchanges, and verification certificates.

---

## 1. Schema Catalog

| Schema Name | Version | Description | Source File / Model |
| :--- | :--- | :--- | :--- |
| **Automate IR** | `automate.ir.v0.2` | Core derivation graph, ASTs, tensor indices, actions | `schemas/automate-ir-v0.1.json`, `automate/ir/ast.py` |
| **Agent Context** | `automate.context.v1` | Sanitized mathematical state exposed to AI models | `automate/ai/schemas.py::AIContext` |
| **Agent Proposal** | `automate.proposal.v1` | Structured mathematical derivation proposal from AI | `automate/ai/schemas.py::DerivationProposal` |
| **Machine Agent Contract** | `automate.agent.v1` | Stable machine-readable capability, command, rule, and trust manifest for external AI agents | `schemas/automate-agent-v1.json` |
| **Certificate Package** | `automate.cert.v0.2` | Complete machine-auditable verification package | `automate/core/graph.py::export_certificate_package` |

---

## 2. Derivation Graph Schema (`automate.ir.v0.2`)

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "nodes": {
    "<node_id>": {
      "id": "string",
      "expression": {
        "raw_str": "string",
        "ast": {
          "kind": "scalar | variable | binary_op | unary_op | derivative | integral | tensor | action | measure",
          "...": "typed node properties"
        },
        "dimension": "string (SI dimensional formula, e.g. M*L*T^-2)",
        "latex": "string (optional)",
        "sympy_str": "string (optional)",
        "lean_str": "string (optional)"
      },
      "node_kind": "expression | equation | proposition | observable | parameter | trajectory | action | field_equation | tensor",
      "domain": "string",
      "source": "string",
      "status": "VerificationStatus enum",
      "assumptions": ["string (assumption_id)"]
    }
  },
  "edges": {
    "<edge_id>": {
      "id": "string",
      "input_nodes": ["string (node_id)"],
      "output_nodes": ["string (node_id)"],
      "transformation_rule": "string",
      "justification": "string",
      "checker": "sympy | lean4 | numerical | statistical | dimension",
      "status": "VerificationStatus enum",
      "parameters": {},
      "side_conditions": ["string (assumption_id)"],
      "verification_obligations": [
        {
          "type": "string",
          "claim": "string",
          "description": "string"
        }
      ],
      "evidence": {
        "status": "string",
        "passed": "boolean",
        "checker": "string",
        "details": {},
        "graph_id": "string",
        "edge_id": "string"
      },
      "certificate": {
        "rule_name": "string",
        "steps": [],
        "backend_version": "string",
        "execution_time_ms": "number"
      }
    }
  },
  "assumptions": {
    "<assumption_id>": {
      "id": "string",
      "description": "string",
      "formal_predicate": "string",
      "category": "domain_restriction | approximation | constitutive | boundary_condition | symmetry",
      "active": "boolean"
    }
  }
}
```

---

## 3. Controlled Agent Context (`automate.context.v1`)

```json
{
  "schema_version": "automate.context.v1",
  "theory_id": "harmonic_oscillator",
  "theory_name": "Simple Harmonic Oscillator",
  "domain": "classical_mechanics",
  "graph_hash": "a1b2c3d4e5f6... (SHA-256 of mathematical AST)",
  "equations": [
    {
      "id": "node_eom",
      "expression": "m * diff(x(t), t, 2) + k * x(t) = 0",
      "dimension": "M*L*T^-2",
      "latex": "m \\ddot{x} + k x = 0"
    }
  ],
  "nodes": [...],
  "edges": [...],
  "assumptions": [
    {
      "id": "asm_pos_mass",
      "predicate": "m > 0",
      "category": "domain_restriction",
      "active": true
    }
  ],
  "open_obligations": [],
  "verified_edges": ["edge_el"],
  "failed_edges": [],
  "available_rules": [
    {
      "rule_id": "solve_harmonic_oscillator",
      "name": "Harmonic Oscillator General Solution",
      "category": "differential_equations",
      "domain": "classical_mechanics",
      "backend": "sympy"
    }
  ]
}
```

---

## 4. Agent Proposal Schema (`automate.proposal.v1`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AutomateDerivationProposal",
  "type": "object",
  "required": [
    "schema_version",
    "proposal_id",
    "rule",
    "justification",
    "output_nodes"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "automate.proposal.v1"
    },
    "proposal_id": {
      "type": "string"
    },
    "proposal_type": {
      "type": "string",
      "enum": ["derivation", "conjecture", "counterexample", "assumption"]
    },
    "input_nodes": {
      "type": "array",
      "items": {"type": "string"}
    },
    "output_nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "expression"],
        "properties": {
          "id": {"type": "string"},
          "expression": {"type": "string"},
          "dimension": {"type": "string"},
          "latex": {"type": "string"},
          "node_kind": {"type": "string"},
          "domain": {"type": "string"}
        }
      }
    },
    "rule": {
      "type": "string"
    },
    "justification": {
      "type": "string"
    },
    "proposed_assumptions": {
      "type": "array",
      "items": {"type": "object"}
    },
    "side_conditions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "target_checker": {
      "type": "string",
      "enum": ["sympy", "lean4", "numerical", "statistical", "dimension"]
    },
    "parameters": {
      "type": "object"
    },
    "origin": {
      "type": "object",
      "properties": {
        "type": {"type": "string"},
        "provider": {"type": "string"},
        "model": {"type": "string"},
        "context_hash": {"type": "string"}
      }
    }
  }
}
```

---

## 5. Certificate Package Specification

When `graph.export_certificate_package(out_dir)` is called, the output directory contains exactly 7 files:

1. **`certificate.json`**: Global verification summary:
   - `graph_id`, `name`, `generated_at`
   - `is_fully_verified`: Boolean (true iff all edges verified with zero failures)
   - `total_nodes`, `total_edges`, `total_assumptions`
   - `edge_status_counts`, `node_status_counts`
   - `failed_derivations`, `invalidated_nodes`
2. **`assumptions.json`**: All declared assumptions and per-node transitive dependency sets.
3. **`obligations.json`**: Side conditions and formal verification obligations per edge.
4. **`evidence.json`**: Concrete backend execution reports, residuals, execution times, and Lean theorem metadata.
5. **`subgraph_expansion.json`**: Lossless micro-step expansions of composite edges.
6. **`provenance.json`**: Complete origin attribution:
   - Git commit or SHA-256 hash
   - Semantic graph hash
   - Backend compiler versions (e.g. `SymPy 1.13.3`, `Lean 4.15.0`)
   - Edge origins (human analytical vs AI proposal)
7. **`manifest.json`**: Cryptographic integrity manifest:
   ```json
   {
     "certificate.json": {
       "sha256": "4b68e9188e72...",
       "size_bytes": 1024
     },
     "assumptions.json": {
       "sha256": "8f3b...",
       "size_bytes": 512
     },
     "obligations.json": { ... },
     "evidence.json": { ... },
     "subgraph_expansion.json": { ... },
     "provenance.json": { ... }
   }
   ```
