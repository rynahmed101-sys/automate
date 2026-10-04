"""Focused tests for numerical convergence evidence and fail-closed diagnostics."""

from automate.backend.numerical_backend import NumericalChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _make_eom_edge(eom: str, rule: str = "numerical_simulation"):
    graph = DerivationGraph(id="numerical_evidence")
    graph.add_node(
        DerivationNode(
            id="eom",
            expression=MathematicalExpression(raw_str=eom),
        )
    )
    graph.add_node(
        DerivationNode(
            id="trajectory",
            expression=MathematicalExpression(raw_str="numerical_trajectory"),
        )
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=["eom"],
        output_nodes=["trajectory"],
        transformation_rule=rule,
        justification="Controlled numerical verification",
        checker="numerical",
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
            "numerical_parameters": {"m": 1.0, "k": 4.0},
            "initial_conditions": {"x": 1.0},
            "initial_velocities": {"x": 0.0},
            "t_max": 10.0,
        },
    )
    graph.add_edge(edge)
    return graph, edge


def test_numerical_report_records_convergence_and_claim_fingerprint():
    graph, edge = _make_eom_edge("m * x_ddot + k * x")
    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert report.status == VerificationStatus.NUMERICALLY_CHECKED

    metrics = report.details["metrics"]
    assert metrics["convergence_probe"] == "passed"
    assert metrics["max_relative_state_difference"] >= 0
    assert len(metrics["claim_fingerprint_sha256"]) == 64
    assert any(step["step"] == "tolerance_refinement_check" for step in report.certificates)


def test_numerical_convergence_gate_can_reject_unstable_result():
    graph, edge = _make_eom_edge("x_ddot + x**3")
    checker = NumericalChecker(convergence_tolerance=1e-15)
    report = checker.verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "refinement" in (report.error_message or "").lower()


def test_energy_diagnostic_unavailable_is_not_success(monkeypatch):
    graph, edge = _make_eom_edge(
        "ignored",
        rule="conserve_energy",
    )
    edge.parameters["coordinates"] = ["x"]
    edge.parameters["parameters"] = {"m": "positive", "k": "positive"}
    edge.parameters["numerical_parameters"] = {"m": 1.0, "k": 4.0}
    graph.get_node("eom").expression.raw_str = (
        "1/2 * m * x_dot**2 - 1/2 * k * x**2"
    )

    checker = NumericalChecker()
    monkeypatch.setattr(
        checker,
        "_check_energy_conservation_numerical",
        lambda *args, **kwargs: (False, None),
    )

    report = checker.verify_edge(edge, graph)

    assert report.passed is False
    assert "could not be evaluated" in (report.error_message or "").lower()


def test_numerical_configuration_rejects_invalid_bounds():
    for kwargs in (
        {"rtol": 0},
        {"atol": 0},
        {"convergence_tolerance": 0},
        {"refinement_factor": 1},
    ):
        try:
            NumericalChecker(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_numerical_interval_rejects_nonpositive_tmax():
    graph, edge = _make_eom_edge("m * x_ddot + k * x")
    edge.parameters["t_max"] = 0

    report = NumericalChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "t_max" in (report.error_message or "")
