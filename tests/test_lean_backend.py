"""
Tests for LeanChecker formal verification backend.
"""

import pytest
from automate.backend.lean_backend import LeanChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_lean_toolchain_detection():
    checker = LeanChecker()
    # If lean is installed on the system (e.g. F:\elan\bin\lean.exe), verify availability
    if checker.is_available():
        assert "Lean" in checker.version
        assert "4." in checker.version


def test_lean_formal_proof_verification():
    checker = LeanChecker()
    if not checker.is_available():
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

    assert report.passed is True
    assert report.status == VerificationStatus.FORMALLY_PROVED
    assert report.backend == "LeanChecker"
    assert "harmonic_oscillator_energy_derivative_vanishes" in report.details["theorem_name"]
    assert report.details["returncode"] == 0
    assert report.proof_script is not None
    assert edge.certificate is not None
    assert "formal_proof_hash" in edge.certificate.metrics



def test_graph_bound_symbolic_algebraic_identity():
    checker = LeanChecker()
    graph = DerivationGraph(id="lean_symbolic_binding")
    graph.add_node(
        DerivationNode(
            id="lhs",
            expression=MathematicalExpression(raw_str="x**2 + 2*x + 1"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="rhs",
            expression=MathematicalExpression(raw_str="(x + 1)**2"),
        )
    )
    edge = DerivationEdge(
        id="edge_symbolic",
        input_nodes=["lhs"],
        output_nodes=["rhs"],
        transformation_rule="algebraic_identity",
        justification="Polynomial expansion",
        checker="lean4",
    )
    graph.add_edge(edge)

    lhs = graph.get_node("lhs")
    rhs = graph.get_node("rhs")
    lean_code, theorem_name = checker._generate_lean_obligation(edge, [lhs], [rhs])

    assert lean_code != "__NOT_APPLICABLE__"
    assert theorem_name.startswith("algebraic_identity_")
    assert "x" in lean_code
    assert "2" in lean_code
    assert "x ** 2" not in lean_code


def test_graph_bound_wrong_symbolic_identity_is_not_certified():
    checker = LeanChecker()
    graph = DerivationGraph(id="lean_symbolic_negative")
    graph.add_node(
        DerivationNode(
            id="lhs",
            expression=MathematicalExpression(raw_str="x**2 + 2*x + 1"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="rhs",
            expression=MathematicalExpression(raw_str="x**2 + 2*x"),
        )
    )
    edge = DerivationEdge(
        id="edge_symbolic_wrong",
        input_nodes=["lhs"],
        output_nodes=["rhs"],
        transformation_rule="algebraic_identity",
        justification="Adversarial wrong identity",
        checker="lean4",
    )
    graph.add_edge(edge)

    lean_code, theorem_name = checker._generate_lean_obligation(
        edge,
        [graph.get_node("lhs")],
        [graph.get_node("rhs")],
    )

    assert lean_code != "__NOT_APPLICABLE__"
    if checker.is_available():
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.FAILED
        assert report.passed is False
    else:
        # Translation is still generated from the actual graph; execution is
        # honestly deferred when no Lean compiler is available.
        assert theorem_name.startswith("algebraic_identity_")
