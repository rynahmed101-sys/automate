"""
Tests for StatisticalChecker parameter estimation backend.
Updated to use model-aware fitting. The model must be specified explicitly.
"""

import pytest
import numpy as np
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
            "model": "cosine",
            "A": 1.0,
            "omega": 2.0,
            "phi": 0.0,
            "t_data": np.linspace(0, 10, 50).tolist(),
            "x_obs": (
                np.cos(2.0 * np.linspace(0, 10, 50))
                + 0.05 * np.random.default_rng(42).normal(size=50)
            ).tolist(),
            "noise_std": 0.05,
            "data_source": "observed",
            "data_id": "test-observed-cosine-v1",
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


def test_empirical_inference_rejects_implicit_synthetic_data():
    graph = DerivationGraph(id="stats_synthetic_rejection")
    graph.add_node(
        DerivationNode(
            id="sol",
            expression=MathematicalExpression(raw_str="A * cos(omega * t + phi)"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="fit",
            expression=MathematicalExpression(raw_str="fit"),
        )
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Empirical fitting",
        checker="statistical",
        parameters={
            "model": "cosine",
            "A": 1.0,
            "omega": 2.0,
            "phi": 0.0,
            "n_points": 50,
            "noise_std": 0.05,
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert "explicit t_data and x_obs" in (report.error_message or "")
    assert "observational evidence" in (report.error_message or "")


def test_empirical_inference_records_data_fingerprint_and_sigma_mode():
    graph = DerivationGraph(id="stats_provenance")
    graph.add_node(
        DerivationNode(
            id="sol",
            expression=MathematicalExpression(raw_str="a * t + b"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="fit",
            expression=MathematicalExpression(raw_str="linear_fit"),
        )
    )
    t_data = np.linspace(0, 5, 20)
    x_obs = 3.0 * t_data + 2.0

    edge = DerivationEdge(
        id="edge",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Linear regression",
        checker="statistical",
        parameters={
            "model": "linear",
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "data_source": "observed",
            "data_id": "test-linear-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert report.details["data_provenance"]["data_id"] == "test-linear-v1"
    assert len(report.details["data_provenance"]["sha256"]) == 64
    assert report.details["goodness_of_fit"]["chi2"] is None
    assert report.details["goodness_of_fit"]["chi2_mode"].startswith("unavailable")


def test_fit_initial_guess_does_not_use_reference_parameters():
    checker = StatisticalChecker()
    params = {"A": 99.0, "omega": 77.0, "phi": 55.0}
    _, names, guesses, _ = checker._build_model("cosine", params, None)

    assert names == ["A", "omega", "phi"]
    assert guesses == [1.2, 1.8, 0.1]

    params["fit_initial_guess"] = {"A": 2.0, "omega": 3.0, "phi": 0.25}
    _, _, explicit_guesses, _ = checker._build_model("cosine", params, None)
    assert explicit_guesses == [2.0, 3.0, 0.25]
