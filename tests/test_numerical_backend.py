"""
Tests for NumericalChecker ODE simulation backend.
Updated to use generalized EoM-string-based simulation.
The backend reads EoM from in_node.expression.raw_str and edge.parameters.
"""

import pytest
from automate.backend.numerical_backend import NumericalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_numerical_ode_simulation():
    """
    Integrates m*x_ddot + k*x = 0 numerically given m=1, k=4.
    The EoM string is read from in_node.expression.raw_str.
    Numerical parameters (m, k values) are in edge.parameters['numerical_parameters'].
    """
    graph = DerivationGraph(id="num_test")

    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x")
    )
    traj_node = DerivationNode(
        id="traj",
        expression=MathematicalExpression(raw_str="numerical_trajectory")
    )
    graph.add_node(eom_node)
    graph.add_node(traj_node)

    edge = DerivationEdge(
        id="edge_sim",
        input_nodes=["eom"],
        output_nodes=["traj"],
        transformation_rule="numerical_simulation",
        justification="RK45 IVP Integration",
        checker="numerical",
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
            "numerical_parameters": {"m": 1.0, "k": 4.0},
            "initial_conditions": {"x": 1.0},
            "initial_velocities": {"x": 0.0},
            "t_max": 10.0,
        }
    )
    graph.add_edge(edge)

    checker = NumericalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True, f"Expected pass, got: {report.error_message}"
    assert report.status == VerificationStatus.NUMERICALLY_CHECKED
    assert report.backend == "NumericalChecker"

    metrics = report.details.get("metrics", {})
    assert metrics.get("solver_method") == "RK45"
    assert metrics.get("num_steps", 0) > 0


def test_numerical_unsupported_rule_returns_not_applicable():
    """Non-ODE rules must return NOT_APPLICABLE, not silently run SHO simulation."""
    graph = DerivationGraph(id="na_test")

    in_node = DerivationNode(
        id="in",
        expression=MathematicalExpression(raw_str="x**2 + 2*x + 1")
    )
    out_node = DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str="(x + 1)**2")
    )
    graph.add_node(in_node)
    graph.add_node(out_node)

    edge = DerivationEdge(
        id="edge_alg",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule="algebraic_identity",
        justification="Algebra",
    )
    graph.add_edge(edge)

    checker = NumericalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.status == VerificationStatus.NOT_APPLICABLE
    assert report.passed is False


def test_numerical_checker_rejects_nonpositive_evaluation_budget():
    with pytest.raises(ValueError, match="max_function_evaluations"):
        NumericalChecker(max_function_evaluations=0)


def test_numerical_report_records_execution_budget():
    graph = DerivationGraph(id="num_budget")
    graph.add_node(
        DerivationNode(id="eom", expression=MathematicalExpression(raw_str="m * x_ddot + k * x"))
    )
    graph.add_node(
        DerivationNode(id="traj", expression=MathematicalExpression(raw_str="numerical_trajectory"))
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=["eom"],
        output_nodes=["traj"],
        transformation_rule="numerical_simulation",
        justification="Sandbox budget test",
        checker="numerical",
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
            "numerical_parameters": {"m": 1.0, "k": 4.0},
            "initial_conditions": {"x": 1.0},
            "initial_velocities": {"x": 0.0},
            "t_max": 1.0,
        },
    )
    graph.add_edge(edge)
    report = NumericalChecker(max_function_evaluations=100_000).verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert report.details["metrics"]["max_function_evaluations"] == 100_000
