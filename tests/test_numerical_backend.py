"""
Tests for NumericalChecker ODE simulation backend.
"""

from automate.backend.numerical_backend import NumericalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _make_edge(rule="numerical_simulation"):
    graph = DerivationGraph(id="num_test")
    eom_node = DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x = 0")
    )
    traj_node = DerivationNode(
        id="traj",
        expression=MathematicalExpression(raw_str="numerical_trajectory(t)")
    )
    graph.add_node(eom_node)
    graph.add_node(traj_node)
    edge = DerivationEdge(
        id="edge_sim",
        input_nodes=["eom"],
        output_nodes=["traj"],
        transformation_rule=rule,
        justification="RK45 IVP Integration",
        checker="numerical",
        parameters={"m": 1.0, "k": 4.0, "x0": 1.0, "v0": 0.0, "t_max": 10.0},
    )
    graph.add_edge(edge)
    return graph, edge


def test_numerical_ode_simulation():
    graph, edge = _make_edge()

    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.NUMERICALLY_CHECKED
    assert report.backend == "NumericalChecker"

    metrics = report.details["metrics"]
    assert metrics["max_abs_error"] < 1e-4
    assert metrics["rmse"] < 1e-4
    assert metrics["velocity_max_abs_error"] < 1e-4
    assert metrics["velocity_rmse"] < 1e-4
    assert metrics["energy_drift_relative"] < 1e-4
    assert metrics["solver_method"] == "RK45"


def test_numerical_unknown_rule_is_rejected():
    graph, edge = _make_edge(rule="made_up_rule")

    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "Unsupported numerical transformation rule" in (report.error_message or "")


def test_numerical_rejects_non_harmonic_graph_equation():
    graph, edge = _make_edge()
    graph.nodes["eom"].expression.raw_str = "m * x_ddot + 2 * k * x = 0"

    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "only supports the harmonic oscillator equation" in (report.error_message or "")


def test_numerical_zero_energy_initial_state_is_finite():
    graph, edge = _make_edge()
    edge.parameters.update({"x0": 0.0, "v0": 0.0})

    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is True
    metrics = report.details["metrics"]
    assert metrics["energy_drift_relative"] is None
    assert metrics["energy_drift_absolute"] < 1e-12
