"""
Tests for SymPyChecker symbolic derivation backend.
"""

import pytest
from automate.backend.sympy_backend import SymPyChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_sympy_euler_lagrange_verification():
    graph = DerivationGraph(id="el_test")

    lagr_node = DerivationNode(
        id="lagr",
        expression=MathematicalExpression(
            raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            dimension="M*L^2*T^-2"
        )
    )
    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(
            raw_str="m * x_ddot + k * x = 0",
            dimension="M*L*T^-2"
        )
    )
    graph.add_node(lagr_node)
    graph.add_node(eom_node)

    edge = DerivationEdge(
        id="edge_el",
        input_nodes=["lagr"],
        output_nodes=["eom"],
        transformation_rule="euler_lagrange",
        justification="Hamilton's Principle"
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.backend == "SymPyChecker"
    assert report.details["zero_test_passed"] is True
    assert len(report.certificates) == 4


def test_sympy_energy_conservation_verification():
    graph = DerivationGraph(id="energy_test")

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
        expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 + 1/2 * k * x**2")
    )
    graph.add_node(lagr_node)
    graph.add_node(eom_node)
    graph.add_node(energy_node)

    edge = DerivationEdge(
        id="edge_energy",
        input_nodes=["lagr", "eom"],
        output_nodes=["energy"],
        transformation_rule="conserve_energy",
        justification="Noether's Theorem"
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["is_conserved"] is True


def test_sympy_harmonic_solution_verification():
    graph = DerivationGraph(id="sol_test")

    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x = 0")
    )
    sol_node = DerivationNode(
        id="sol",
        expression=MathematicalExpression(raw_str="x(t) = A * cos(omega * t + phi)")
    )
    graph.add_node(eom_node)
    graph.add_node(sol_node)

    edge = DerivationEdge(
        id="edge_sol",
        input_nodes=["eom"],
        output_nodes=["sol"],
        transformation_rule="solve_harmonic_oscillator",
        justification="Linear ODE Solution"
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["satisfies_ode"] is True


def test_sympy_euler_lagrange_uses_actual_graph_expression():
    graph = DerivationGraph(id="graph_driven_el_test")
    lagr = DerivationNode(
        id="lagr",
        expression=MathematicalExpression(
            raw_str="1/2 * m * theta_dot**2 - m * g * l * (1 - cos(theta))"
        )
    )
    eom = DerivationNode(
        id="eom",
        expression=MathematicalExpression(
            raw_str="m * theta_ddot + m * g * l * sin(theta) = 0"
        )
    )
    graph.add_node(lagr)
    graph.add_node(eom)
    edge = DerivationEdge(
        id="edge_el_pendulum",
        input_nodes=["lagr"],
        output_nodes=["eom"],
        transformation_rule="euler_lagrange",
        justification="Euler-Lagrange equation for a pendulum",
        parameters={"coordinate": "theta", "time_variable": "t"},
    )
    graph.add_edge(edge)

    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is True
    assert report.details["zero_test_passed"] is True
    assert "g" in report.details["lagrangian"]


def test_sympy_euler_lagrange_rejects_wrong_graph_equation():
    graph = DerivationGraph(id="graph_driven_bad_el")
    lagr = DerivationNode(
        id="lagr",
        expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2")
    )
    eom = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot - k * x = 0")
    )
    graph.add_node(lagr)
    graph.add_node(eom)
    edge = DerivationEdge(
        id="edge_bad_el",
        input_nodes=["lagr"],
        output_nodes=["eom"],
        transformation_rule="euler_lagrange",
        justification="Intentionally incorrect equation",
    )
    graph.add_edge(edge)

    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED


def test_sympy_energy_conservation_rejects_damped_system():
    graph = DerivationGraph(id="damped_energy_test")
    eom = DerivationNode(
        id="eom",
        expression=MathematicalExpression(
            raw_str="m * x_ddot + c * x_dot + k * x = 0"
        )
    )
    energy = DerivationNode(
        id="energy",
        expression=MathematicalExpression(
            raw_str="1/2 * m * x_dot**2 + 1/2 * k * x**2"
        )
    )
    graph.add_node(eom)
    graph.add_node(energy)
    edge = DerivationEdge(
        id="edge_damped_energy",
        input_nodes=["eom"],
        output_nodes=["energy"],
        transformation_rule="conserve_energy",
        justification="Intentionally incorrect conservation claim",
    )
    graph.add_edge(edge)

    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED


def test_sympy_harmonic_solution_rejects_wrong_frequency():
    graph = DerivationGraph(id="bad_frequency_test")
    eom = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x = 0")
    )
    sol = DerivationNode(
        id="sol",
        expression=MathematicalExpression(raw_str="x(t) = A * cos(3 * t + phi)")
    )
    graph.add_node(eom)
    graph.add_node(sol)
    edge = DerivationEdge(
        id="edge_bad_frequency",
        input_nodes=["eom"],
        output_nodes=["sol"],
        transformation_rule="solve_harmonic_oscillator",
        justification="Intentionally incorrect frequency",
    )
    graph.add_edge(edge)

    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED


def test_sympy_unsupported_rule_is_rejected():
    graph = DerivationGraph(id="unsupported_symbolic_test")
    a = DerivationNode(id="a", expression=MathematicalExpression(raw_str="x"))
    b = DerivationNode(id="b", expression=MathematicalExpression(raw_str="x"))
    graph.add_node(a)
    graph.add_node(b)
    edge = DerivationEdge(
        id="edge_unknown",
        input_nodes=["a"],
        output_nodes=["b"],
        transformation_rule="made_up_symbolic_rule",
        justification="Unknown",
    )
    graph.add_edge(edge)

    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "Unsupported symbolic transformation rule" in (report.error_message or "")


def test_sympy_parser_rejects_python_execution_payload():
    from automate.backend.sympy_utils import safe_parse_expr

    with pytest.raises((NameError, ValueError, SyntaxError)):
        safe_parse_expr("__import__('os').system('echo SHOULD_NOT_RUN')")
