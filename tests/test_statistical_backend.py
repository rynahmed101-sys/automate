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


def test_statistical_checker_uses_supplied_observations():
    import numpy as np

    t = np.linspace(0, 10, 80)
    x = 1.0 * np.cos(2.0 * t + 0.1)
    graph = DerivationGraph(id="observed_stats_test")
    graph.add_node(DerivationNode(
        id="model",
        expression=MathematicalExpression(raw_str="x(t) = A*cos(omega*t + phi)")
    ))
    graph.add_node(DerivationNode(
        id="fit",
        expression=MathematicalExpression(raw_str="observed fit")
    ))
    edge = DerivationEdge(
        id="edge_observed_fit",
        input_nodes=["model"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Observed harmonic data",
        checker="statistical",
        parameters={
            "m": 1.0,
            "k": 4.0,
            "t_data": t.tolist(),
            "x_data": x.tolist(),
            "sigma_data": [0.01] * len(t),
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)
    assert report.passed is True
    assert report.details["data_source"] == "observed"
    assert report.details["random_seed"] is None
    assert abs(report.details["parameter_estimates"]["frequency_omega"]["estimate"] - 2.0) < 1e-6


def test_statistical_checker_rejects_missing_observation_pair():
    graph = DerivationGraph(id="bad_observed_stats")
    graph.add_node(DerivationNode(
        id="model",
        expression=MathematicalExpression(raw_str="x(t) = A*cos(omega*t + phi)")
    ))
    graph.add_node(DerivationNode(
        id="fit",
        expression=MathematicalExpression(raw_str="fit")
    ))
    edge = DerivationEdge(
        id="edge_bad_observed_fit",
        input_nodes=["model"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Invalid observed data",
        checker="statistical",
        parameters={"x_data": [1.0, 2.0, 3.0]},
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert "Both t_data and x_data" in (report.error_message or "")
