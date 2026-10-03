"""
Tests for StatisticalChecker parameter estimation backend.
"""

import pytest
from automate.backend.statistical_backend import StatisticalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_statistical_parameter_inference():
    graph = DerivationGraph(id="stats_test")

    sol_node = DerivationNode(
        id="sol",
        expression=MathematicalExpression(raw_str="x(t) = A*cos(omega*t + phi)")
    )
    fit_node = DerivationNode(
        id="fit",
        expression=MathematicalExpression(raw_str="omega_fit = 2.0 rad/s")
    )
    graph.add_node(sol_node)
    graph.add_node(fit_node)

    edge = DerivationEdge(
        id="edge_fit",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Least Squares Non-linear Regression",
        checker="statistical",
        parameters={"m": 1.0, "k": 4.0, "n_points": 50, "noise_std": 0.05}
    )
    graph.add_edge(edge)

    checker = StatisticalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.STATISTICALLY_CHECKED
    assert report.backend == "StatisticalChecker"

    gof = report.details["goodness_of_fit"]
    assert 0.5 <= gof["reduced_chi2"] <= 2.0
    assert gof["r_squared"] > 0.95

    estimates = report.details["parameter_estimates"]
    # True omega = sqrt(4/1) = 2.0 rad/s
    omega_est = estimates["frequency_omega"]["estimate"]
    assert abs(omega_est - 2.0) < 0.1
