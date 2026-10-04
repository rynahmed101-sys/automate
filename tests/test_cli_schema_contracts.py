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
