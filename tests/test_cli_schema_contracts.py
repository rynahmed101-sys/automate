"""Contract tests for the small public calculator schema surface."""

import json
from click.testing import CliRunner
from automate.cli import main

def test_schema_ir_returns_canonical_schema():
    result = CliRunner().invoke(main, ["schema", "--name", "ir"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-ir-v0.1.json")

def test_schema_tensor_returns_canonical_tensor_contract():
    result = CliRunner().invoke(main, ["schema", "--name", "tensor"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["$id"].endswith("/automate-tensor-v1.json")
    assert "lhs" in payload["properties"]

def test_schema_rejects_removed_ai_contracts():
    result = CliRunner().invoke(main, ["schema", "--name", "agent"])
    assert result.exit_code != 0
