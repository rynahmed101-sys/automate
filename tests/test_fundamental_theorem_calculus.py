"""Acceptance coverage for the Fundamental Theorem of Calculus capability."""

from automate.backend.sympy_backend import SymPyChecker
from automate.ir.assumptions import Assumption
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph_edge(mode, inputs, output, params, *, with_continuity=True):
    graph = DerivationGraph(id=f"ftc_{mode}")
    if with_continuity:
        graph.add_assumption(
            Assumption(
                id="ftc_integrand_continuous_on_interval",
                description="The represented integrand is continuous on the represented interval.",
                category="regularity",
                formal_predicate="integrand_continuous_on_interval",
            )
        )
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(
            DerivationNode(
                id=node_id,
                expression=MathematicalExpression(raw_str=expression),
            )
        )
    graph.add_node(
        DerivationNode(
            id="out",
            expression=MathematicalExpression(raw_str=output),
        )
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=input_ids,
        output_nodes=["out"],
        transformation_rule="fundamental_theorem_calculus",
        justification="Stage 1B Fundamental Theorem of Calculus acceptance",
        checker="sympy",
        parameters=params,
        side_conditions=["ftc_integrand_continuous_on_interval"],
    )
    graph.add_edge(edge)
    return graph, edge


def test_ftc_part_ii_evaluates_definite_integral_from_antiderivative():
    graph, edge = _graph_edge(
        "evaluation",
        ["2*x", "x**2"],
        "9",
        {
            "mode": "evaluation",
            "variable": "x",
            "integration_variable": "x",
            "lower": "0",
            "upper": "3",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["expected_integral"] == "9"


def test_ftc_part_i_verifies_accumulation_function_derivative():
    graph, edge = _graph_edge(
        "accumulation_derivative",
        ["2*t", "x**2"],
        "2*x",
        {
            "mode": "accumulation_derivative",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["derivative_residual"] == "0"
    assert report.details["anchor_residual"] == "0"


def test_ftc_part_ii_rejects_wrong_integral_value():
    graph, edge = _graph_edge(
        "evaluation",
        ["2*t", "t**2"],
        "8",
        {
            "mode": "evaluation",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
            "upper": "3",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_ftc_rejects_non_antiderivative():
    graph, edge = _graph_edge(
        "evaluation",
        ["2*t", "t**3"],
        "9",
        {
            "mode": "evaluation",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
            "upper": "3",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_ftc_part_i_rejects_wrong_accumulation_anchor():
    graph, edge = _graph_edge(
        "accumulation_derivative",
        ["2*t", "x**2 + 1"],
        "2*x",
        {
            "mode": "accumulation_derivative",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert "anchoring" in (report.error_message or "").lower()


def test_ftc_fails_closed_without_continuity_obligation():
    graph, edge = _graph_edge(
        "evaluation",
        ["2*t", "t**2"],
        "9",
        {
            "mode": "evaluation",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
            "upper": "3",
        },
        with_continuity=False,
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.CONDITIONAL
    assert not report.passed


def test_ftc_rejects_mismatched_variable_dependency():
    graph, edge = _graph_edge(
        "evaluation",
        ["2*u", "t**2"],
        "9",
        {
            "mode": "evaluation",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
            "upper": "3",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed


def test_ftc_part_i_rejects_output_not_equal_to_integrand_at_x():
    graph, edge = _graph_edge(
        "accumulation_derivative",
        ["2*t", "x**2"],
        "3*x",
        {
            "mode": "accumulation_derivative",
            "variable": "x",
            "integration_variable": "t",
            "lower": "0",
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
