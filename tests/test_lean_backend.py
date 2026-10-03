"""
Tests for LeanChecker formal verification backend.
"""

import os

import pytest
from automate.backend.lean_backend import LeanChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _lean_required() -> bool:
    return os.environ.get("AUTOMATE_REQUIRE_LEAN") == "1"


def test_lean_toolchain_detection():
    checker = LeanChecker()
    if _lean_required():
        assert checker.is_available(), "Lean 4 must be installed for the enforced CI test matrix."
        assert "Lean" in checker.version
        assert "4." in checker.version
    elif checker.is_available():
        assert "Lean" in checker.version
        assert "4." in checker.version


def test_lean_formal_proof_verification():
    checker = LeanChecker()
    if not checker.is_available():
        if _lean_required():
            pytest.fail("Lean 4 compiler is required but was not detected in this environment.")
        pytest.skip("Lean 4 compiler not available in test environment.")

    graph = DerivationGraph(id="lean_test")

    lagr_node = DerivationNode(
        id="lagr",
        expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2")
    )
    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x = 0")
    )
    energy_node = DerivationNode(
        id="energy",
        expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 + 1/2 * k * x**2 = E")
    )
    graph.add_node(lagr_node)
    graph.add_node(eom_node)
    graph.add_node(energy_node)

    edge = DerivationEdge(
        id="edge_formal_cons",
        input_nodes=["lagr", "eom"],
        output_nodes=["energy"],
        transformation_rule="conserve_energy",
        justification="Noether's Theorem",
        checker="lean4"
    )
    graph.add_edge(edge)

    report = checker.verify_edge(edge, graph)

    assert report.passed is True, report.error_message or str(report.details)
    assert report.status == VerificationStatus.FORMALLY_PROVED
    assert report.backend == "LeanChecker"
    assert "harmonic_oscillator_energy_derivative_vanishes" in report.details["theorem_name"]
    assert report.details["returncode"] == 0
    assert report.proof_script is not None
    assert edge.certificate is not None
    assert "formal_proof_hash" in edge.certificate.metrics
