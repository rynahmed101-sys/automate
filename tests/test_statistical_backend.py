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
    assert gof["chi2_mode"] == "known_observation_sigma"
    assert gof["chi2_two_sided_p_value"] > 0.05
    assert gof["chi2_compatibility_interval"][0] <= gof["chi2"] <= gof["chi2_compatibility_interval"][1]
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
            "x_obs": (x_obs + 0.1 * np.random.default_rng(11).normal(size=len(x_obs))).tolist(),
            "noise_std": 0.1,
            "gof_confidence_level": 0.95,
            "data_source": "observed",
            "data_id": "test-linear-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert report.details["data_provenance"]["data_id"] == "test-linear-v1"
    assert len(report.details["data_provenance"]["sha256"]) == 64
    assert report.details["goodness_of_fit"]["chi2"] is not None
    assert report.details["goodness_of_fit"]["chi2_mode"] == "known_observation_sigma"
    assert report.details["goodness_of_fit"]["gof_confidence_level"] == 0.95



def test_empirical_inference_rejects_model_that_does_not_match_graph_claim():
    """Observed data cannot rescue a statistical model unrelated to the graph expression."""
    graph = DerivationGraph(id="stats_graph_binding")
    graph.add_node(
        DerivationNode(
            id="sol",
            expression=MathematicalExpression(raw_str="A * sin(omega * t + phi)"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="fit",
            expression=MathematicalExpression(raw_str="omega_fit"),
        )
    )

    t_data = np.linspace(0, 10, 50)
    x_obs = np.cos(2.0 * t_data)

    edge = DerivationEdge(
        id="edge",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Graph-bound model test",
        checker="statistical",
        parameters={
            "model": "cosine",
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "noise_std": 0.05,
            "data_source": "observed",
            "data_id": "binding-negative-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "does not match the graph input claim" in (report.error_message or "")


def test_empirical_expression_model_cannot_override_graph_expression():
    """The arbitrary-expression path must not replace the graph model with a different expression."""
    graph = DerivationGraph(id="stats_expression_binding")
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
        justification="Graph-bound expression test",
        checker="statistical",
        parameters={
            "model": "expression",
            "expression_str": "a * t**2 + b",
            "model_parameters": ["a", "b"],
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "noise_std": 0.1,
            "data_source": "observed",
            "data_id": "binding-expression-negative-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "does not match the graph input claim" in (report.error_message or "")



def test_empirical_inference_rejects_locally_non_identifiable_model():
    """A rank-deficient model Jacobian must not receive STATISTICALLY_CHECKED status."""
    graph = DerivationGraph(id="stats_identifiability")
    graph.add_node(
        DerivationNode(
            id="sol",
            expression=MathematicalExpression(raw_str="a * t + b * t"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="fit",
            expression=MathematicalExpression(raw_str="a_fit, b_fit"),
        )
    )

    t_data = np.linspace(0, 5, 20)
    x_obs = 3.0 * t_data

    edge = DerivationEdge(
        id="edge",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Identifiability test",
        checker="statistical",
        parameters={
            "model": "expression",
            "model_parameters": ["a", "b"],
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "noise_std": 0.1,
            "data_source": "observed",
            "data_id": "identifiability-negative-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "not locally identifiable" in (report.error_message or "")

def test_statistical_report_records_graph_and_evidence_fingerprints():
    graph = DerivationGraph(id="stats_fingerprint")
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
        justification="Graph-bound provenance test",
        checker="statistical",
        parameters={
            "model": "linear",
            "t_data": t_data.tolist(),
            "x_obs": (x_obs + 0.1 * np.random.default_rng(12).normal(size=len(x_obs))).tolist(),
            "noise_std": 0.1,
            "gof_confidence_level": 0.95,
            "data_source": "observed",
            "data_id": "binding-positive-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert len(report.details["claim_fingerprint_sha256"]) == 64
    assert len(report.details["evidence_fingerprint_sha256"]) == 64
    assert report.details["graph_claim_binding"]["model_expression_equivalent"] is True


def test_empirical_inference_without_uncertainty_cannot_be_statistically_checked():
    graph = DerivationGraph(id="stats_no_uncertainty")
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
        justification="No uncertainty negative test",
        checker="statistical",
        parameters={
            "model": "linear",
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "data_source": "observed",
            "data_id": "no-uncertainty-negative-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "requires positive observational uncertainty" in (report.error_message or "")


def test_empirical_inference_rejects_invalid_gof_confidence_level():
    graph = DerivationGraph(id="stats_bad_confidence")
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
        justification="Invalid confidence test",
        checker="statistical",
        parameters={
            "model": "linear",
            "t_data": t_data.tolist(),
            "x_obs": x_obs.tolist(),
            "noise_std": 0.1,
            "gof_confidence_level": 1.0,
            "data_source": "observed",
            "data_id": "bad-confidence-v1",
        },
    )
    graph.add_edge(edge)

    report = StatisticalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "confidence level" in (report.error_message or "")

def test_fit_initial_guess_does_not_use_reference_parameters():
    checker = StatisticalChecker()
    params = {"A": 99.0, "omega": 77.0, "phi": 55.0}
    _, names, guesses, _ = checker._build_model("cosine", params, None)

    assert names == ["A", "omega", "phi"]
    assert guesses == [1.2, 1.8, 0.1]

    params["fit_initial_guess"] = {"A": 2.0, "omega": 3.0, "phi": 0.25}
    _, _, explicit_guesses, _ = checker._build_model("cosine", params, None)
    assert explicit_guesses == [2.0, 3.0, 0.25]
