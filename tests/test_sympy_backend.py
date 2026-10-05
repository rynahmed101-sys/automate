"""
Tests for SymPyChecker symbolic derivation backend.
Updated to use generalized LagrangianSystem-based verification.
The new backend reads graph content and edge parameters — coordinates must be explicit.
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
        justification="Hamilton's Principle",
        # NEW: generalized backend requires coordinates and parameters
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
        }
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.backend == "SymPyChecker"
    # Details now from LagrangianSystem, not hardcoded
    assert report.details.get("all_passed") is True


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
        justification="Noether's Theorem",
        # NEW: generalized backend requires coordinates and parameters
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
        }
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    # Details now from LagrangianSystem.verify_energy_conservation
    assert report.details.get("conserved") is True


def test_sympy_harmonic_solution_verification():
    """
    Verifies that x(t) = A*cos(omega*t + phi) with omega = sqrt(k/m)
    satisfies the EoM  m*x_ddot + k*x = 0  by substitution and residual check.
    """
    graph = DerivationGraph(id="sol_test")

    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x = 0")
    )
    sol_node = DerivationNode(
        id="sol",
        # Solution as explicit function — the backend will substitute into EoM
        expression=MathematicalExpression(raw_str="A * cos(sqrt(k/m) * t + phi)")
    )
    graph.add_node(eom_node)
    graph.add_node(sol_node)

    edge = DerivationEdge(
        id="edge_sol",
        input_nodes=["eom"],
        output_nodes=["sol"],
        transformation_rule="solve_harmonic_oscillator",
        justification="Linear ODE Solution",
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
        }
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True, f"Expected pass, got: {report.error_message}"
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details.get("satisfies_ode") is True


def test_sympy_algebraic_identity():
    """Algebraic identity check still works without coordinates."""
    graph = DerivationGraph(id="alg_test")

    in_node = DerivationNode(
        id="in",
        expression=MathematicalExpression(raw_str="(x + 1)**2")
    )
    out_node = DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str="x**2 + 2*x + 1")
    )
    graph.add_node(in_node)
    graph.add_node(out_node)

    edge = DerivationEdge(
        id="edge_alg",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule="algebraic_identity",
        justification="Binomial expansion",
    )
    graph.add_edge(edge)

    checker = SymPyChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
