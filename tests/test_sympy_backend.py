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
