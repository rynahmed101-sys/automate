"""
Tests for NumericalChecker ODE simulation backend.
"""

import pytest
from automate.backend.numerical_backend import NumericalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_numerical_ode_simulation():
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
        transformation_rule="numerical_simulation",
        justification="RK45 IVP Integration",
        checker="numerical",
        parameters={"m": 1.0, "k": 4.0, "x0": 1.0, "v0": 0.0, "t_max": 10.0}
    )
    graph.add_edge(edge)

    checker = NumericalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.NUMERICALLY_CHECKED
    assert report.backend == "NumericalChecker"

    metrics = report.details["metrics"]
    assert metrics["max_abs_error"] < 1e-4
    assert metrics["rmse"] < 1e-4
    assert metrics["energy_drift_relative"] < 1e-4
    assert metrics["solver_method"] == "RK45"
