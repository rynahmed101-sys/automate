"""
Tests for Machine-Readable CLI commands and JSON mode (--json).
Tests capabilities, context, validate, propose, research, and schema commands.
"""

import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from automate.cli import main


def test_cli_capabilities_json():
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "0.2.0"
    assert data["ir"] is True
    assert data["tensors"] is True
    assert data["differential_geometry"] is True
    assert data["symbolic"] is True
    assert "mock" in data["providers"]


def test_cli_context_json():
    runner = CliRunner()
    result = runner.invoke(main, ["context", "examples/harmonic_oscillator.yaml", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "automate.context.v1"
    assert data["theory_id"] == "harmonic_oscillator"
    assert len(data["nodes"]) > 0
    assert len(data["available_rules"]) > 0
    assert "graph_hash" in data


def test_cli_validate_json(tmp_path):
    runner = CliRunner()

    valid_proposal = {
        "schema_version": "automate.proposal.v1",
        "proposal_id": "test_prop_001",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [
            {
                "id": "node_sol",
                "expression": "x(t) = A*cos(omega*t)",
                "dimension": "L",
                "node_kind": "equation"
            }
        ],
        "rule": "solve_harmonic_oscillator",
        "justification": "General linear ODE solution ansatz",
        "target_checker": "sympy",
        "origin": {"type": "ai", "provider": "mock"}
    }

    prop_file = tmp_path / "valid_prop.json"
    prop_file.write_text(json.dumps(valid_proposal), encoding="utf-8")

    result = runner.invoke(main, ["validate", str(prop_file), "--theory", "examples/harmonic_oscillator.yaml", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["is_valid"] is True
    assert data["proposal_id"] == "test_prop_001"


def test_cli_propose_dry_run_json():
    runner = CliRunner()
    result = runner.invoke(main, [
        "propose",
        "examples/harmonic_oscillator.yaml",
        "--request", "Solve harmonic oscillator",
        "--provider", "mock",
        "--dry-run",
        "--json"
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["graph_updated"] is False
    assert "edge_id" in data


def test_cli_research_json(tmp_path):
    runner = CliRunner()
    out_dir = tmp_path / "res_out"
    result = runner.invoke(main, [
        "research",
        "examples/harmonic_oscillator.yaml",
        "--provider", "mock",
        "--max-steps", "1",
        "--output-dir", str(out_dir),
        "--json"
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_steps"] == 1
    assert len(data["trace"]) == 1
    assert (out_dir / "research_graph.json").exists()
    assert (out_dir / "research_trace.json").exists()


def test_cli_schema_json():
    runner = CliRunner()
    result = runner.invoke(main, ["schema", "--name", "ir"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "$schema" in data or "title" in data or "type" in data
