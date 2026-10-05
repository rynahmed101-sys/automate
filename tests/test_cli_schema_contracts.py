"""Contract tests for the machine-readable schema discovery CLI."""

import json

from click.testing import CliRunner

from automate.cli import main


def test_schema_ir_returns_canonical_schema():
    result = CliRunner().invoke(main, ["schema", "--name", "ir"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-ir-v0.1.json")


def test_schema_proposal_returns_proposal_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "proposal"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-proposal-v1.json")
    assert "rule" in payload["properties"]
    assert "output_nodes" in payload["properties"]


def test_schema_context_returns_context_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "context"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-context-v1.json")
    assert "theory_id" in payload["properties"]
    assert "graph_hash" in payload["properties"]


def test_schema_rejects_unknown_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "certificate"])

    assert result.exit_code != 0


def test_schema_tensor_returns_canonical_tensor_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "tensor"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-tensor-v1.json")
    assert "lhs" in payload["properties"]
    assert "TensorExpression" in payload.get("$defs", {})


def test_schema_agent_returns_machine_agent_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "agent"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "automate.agent.v1"
    assert len(payload["rules"]) == 72
    assert {"vector_add", "vector_dot", "matrix_multiply", "matrix_inverse", "matrix_rref", "linear_system_solve", "matrix_characteristic_polynomial", "matrix_eigenvalues", "matrix_eigenvector", "matrix_diagonalize"}.issubset({rule["rule_id"] for rule in payload["rules"]})
    assert {"discover", "context", "validate", "propose_dry_run", "propose_apply",
            "research", "check", "prove", "simulate", "stats",
            "query_assumptions", "expand", "report", "export_certificate",
            "schema"}.issubset(payload["commands"])
    assert "capability_catalog" in payload
