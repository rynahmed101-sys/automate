"""
End-to-End integration tests for Automate.
"""

from pathlib import Path
import pytest
from automate.theory.parser import parse_theory_file
from automate.demo import run_harmonic_oscillator_demo


def test_theory_file_parsing():
    yaml_path = Path(__file__).parent.parent / "examples" / "harmonic_oscillator.yaml"
    graph = parse_theory_file(yaml_path)

    assert graph.id == "harmonic_oscillator"
    assert len(graph.nodes) == 6
    assert len(graph.edges) == 5
    assert len(graph.assumptions) == 4
    assert graph.validate_dag() is True


def test_full_demo_execution(tmp_path):
    # Run the demo producing artifacts into tmp_path
    exit_code = run_harmonic_oscillator_demo(str(tmp_path))
    assert exit_code == 0

    assert (tmp_path / "harmonic_oscillator.html").exists()
    assert (tmp_path / "derivation_graph.json").exists()
    assert (tmp_path / "verification_report.json").exists()
