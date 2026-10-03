"""
Tests for StatisticalChecker parameter estimation backend.
Updated to use model-aware fitting. The model must be specified explicitly.
"""

import pytest
from automate.backend.statistical_backend import StatisticalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def test_statistical_parameter_inference():
    """
    Fit a cosine model to synthetic SHO data.
    True omega = sqrt(k/m) = sqrt(4/1) = 2.0 rad/s.
    Model must be explicit (no default).
    """
    graph = DerivationGraph(id="stats_test")

    sol_node = DerivationNode(
        id="sol",
        expression=MathematicalExpression(raw_str="A * cos(omega * t + phi)")
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
        parameters={
            "model": "cosine",      # NEW: model must be explicit
            "A": 1.0,
            "omega": 2.0,           # true omega = sqrt(k/m) = 2.0
            "phi": 0.0,
            "n_points": 50,
            "noise_std": 0.05,
        }
    )
    graph.add_edge(edge)

    checker = StatisticalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.passed is True, f"Expected pass, got: {report.error_message}"
    assert report.status == VerificationStatus.STATISTICALLY_CHECKED
    assert report.backend == "StatisticalChecker"

    gof = report.details["goodness_of_fit"]
    assert 0.3 <= gof["reduced_chi2"] <= 3.0
    assert gof["r_squared"] > 0.90

    estimates = report.details["parameter_estimates"]
    # True omega = 2.0 rad/s — fitted value should be close
    omega_est = estimates["omega"]["estimate"]
    assert abs(omega_est - 2.0) < 0.15


def test_statistical_not_applicable_for_euler_lagrange():
    """Statistical checker must return NOT_APPLICABLE for euler_lagrange."""
    graph = DerivationGraph(id="na_test")

    in_node = DerivationNode(
        id="in",
        expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2")
    )
    out_node = DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str="m * x_ddot + k * x")
    )
    graph.add_node(in_node)
    graph.add_node(out_node)

    edge = DerivationEdge(
        id="edge_el",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule="euler_lagrange",
        justification="EL equation",
    )
    graph.add_edge(edge)

    checker = StatisticalChecker()
    report = checker.verify_edge(edge, graph)

    assert report.status == VerificationStatus.NOT_APPLICABLE
    assert report.passed is False
