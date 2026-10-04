"""End-to-end machine-readable conformance tests for AI clients."""

import json
from pathlib import Path

from click.testing import CliRunner

from automate.cli import main


def test_machine_client_workflow(tmp_path):
    runner = CliRunner()

    capabilities = runner.invoke(main, ["capabilities", "--json"])
    assert capabilities.exit_code == 0, capabilities.output
    caps = json.loads(capabilities.output)
    assert caps["schema_version"] == "0.2.0"
    assert caps["tensors"] is True
    assert caps["providers"]

    context = runner.invoke(
        main, ["context", "examples/harmonic_oscillator.yaml", "--json"]
    )
    assert context.exit_code == 0, context.output
    ctx = json.loads(context.output)
    assert ctx["schema_version"] == "automate.context.v1"
    assert ctx["graph_hash"]
    assert ctx["available_rules"]

    schema = runner.invoke(main, ["schema", "--name", "tensor"])
    assert schema.exit_code == 0, schema.output
    assert json.loads(schema.output)["$id"].endswith("/automate-tensor-v1.json")

    proposal = {
        "schema_version": "automate.proposal.v1",
        "proposal_id": "machine_client_001",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{
            "id": "node_sol",
            "expression": "x(t) = A*cos(omega*t)",
            "dimension": "L",
            "node_kind": "equation"
        }],
        "rule": "solve_harmonic_oscillator",
        "justification": "Machine-readable workflow contract test.",
        "target_checker": "sympy",
        "parameters": {
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
            "omega": "sqrt(k/m)"
        },
        "origin": {
            "type": "ai",
            "provider": "conformance-test",
            "context_hash": ctx["graph_hash"]
        }
    }
    proposal_file = tmp_path / "proposal.json"
    proposal_file.write_text(json.dumps(proposal), encoding="utf-8")

    validation = runner.invoke(
        main, [
            "validate", str(proposal_file),
            "--theory", "examples/harmonic_oscillator.yaml", "--json"
        ]
    )
    assert validation.exit_code == 0, validation.output
    assert json.loads(validation.output)["is_valid"] is True

    dry_run = runner.invoke(
        main, [
            "propose", "examples/harmonic_oscillator.yaml",
            "--proposal", str(proposal_file), "--dry-run", "--json"
        ]
    )
    assert dry_run.exit_code == 0, dry_run.output
    dry = json.loads(dry_run.output)
    assert dry["success"] is True
    assert dry["graph_updated"] is False
    assert dry["edge_id"]

    research_dir = tmp_path / "research"
    research = runner.invoke(
        main, [
            "research", "examples/harmonic_oscillator.yaml",
            "--provider", "mock", "--max-steps", "1",
            "--output-dir", str(research_dir), "--json"
        ]
    )
    assert research.exit_code == 0, research.output
    trace = json.loads(research.output)
    assert trace["total_steps"] == 1
    assert Path(trace["graph_file"]).exists()

    check = runner.invoke(
        main, ["check", "examples/harmonic_oscillator.yaml", "--json"]
    )
    assert check.exit_code == 0, check.output
    json.loads(check.output)
