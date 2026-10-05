"""Focused Stage 1B derivative and higher-order derivative acceptance tests."""

import pytest
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression

def _graph_edge(input_expr, output_expr, *, parameters=None):
    graph = DerivationGraph(id="derivative_acceptance")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=input_expr)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output_expr)))
    edge = DerivationEdge(id="edge", input_nodes=["in"], output_nodes=["out"],
        transformation_rule="differentiate", justification="Stage 1B derivative acceptance campaign",
        checker="sympy", parameters=parameters or {})
    graph.add_edge(edge)
    return graph, edge

@pytest.mark.parametrize("expr,expected,order", [
    ("x**4 + 3*x**2 - 7*x + 1", "4*x**3 + 6*x - 7", 1),
    ("sin(x)", "-sin(x)", 2),
    ("exp(x)*sin(x)", "-4*(sin(x) + cos(x))*exp(x)", 5),
    ("7", "0", 1),
])
def test_derivative_acceptance_cases(expr, expected, order):
    graph, edge = _graph_edge(expr, expected, parameters={"variable": "x", "order": order})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["order"] == order

def test_first_and_higher_orders_share_one_general_rule():
    for order, expected in [(1, "3*x**2"), (2, "6*x"), (3, "6"), (4, "0")]:
        graph, edge = _graph_edge("x**3", expected, parameters={"variable": "x", "order": order})
        report = SymPyChecker().verify_edge(edge, graph)
        assert report.passed, report.error_message

def test_symbolic_assumptions_are_applied_to_expression_parsing():
    graph, edge = _graph_edge("a*x**2", "2*a*x",
        parameters={"variable": "x", "order": 1, "assumptions": {"a": ["real", "positive"]}})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message

def test_numeric_expression_differentiates_exactly():
    graph, edge = _graph_edge("3.5", "0", parameters={"variable": "x", "order": 3})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message

def test_singular_expression_preserves_domain_information():
    graph, edge = _graph_edge("1/x", "-1/x**2", parameters={"variable": "x", "order": 1})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert "0" in report.details["domain_analysis"]["input_real_domain"]
    assert "0" in report.details["domain_analysis"]["derivative_real_domain"]

def test_boundary_domain_metadata_is_preserved():
    graph, edge = _graph_edge(
        "sqrt(x)", "1/(2*sqrt(x))", parameters={"variable": "x", "order": 1}
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert "0" in report.details["domain_analysis"]["input_real_domain"]
    assert "0" in report.details["domain_analysis"]["derivative_real_domain"]

@pytest.mark.parametrize("expected", ["4*x**2", "3*x**2 + 1"])
def test_incorrect_derivative_is_rejected(expected):
    graph, edge = _graph_edge("x**3", expected, parameters={"variable": "x", "order": 1})
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED

@pytest.mark.parametrize("parameters", [
    {"variable": "x", "order": 0}, {"variable": "x", "order": -1},
    {"variable": "x", "order": 2.0}, {"variable": "x", "order": True},
    {"variable": "", "order": 1}, {"variable": "not-valid", "order": 1},
    {"variable": "x", "order": 1, "assumptions": {"bad-name": "real"}},
    {"variable": "x", "order": 1, "assumptions": {"a": "complex"}},
])
def test_malformed_derivative_parameters_fail_closed(parameters):
    graph, edge = _graph_edge("x", "1", parameters=parameters)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_safe_parser_rejects_malicious_derivative_expression():
    graph, edge = _graph_edge("__import__('os').system('echo bad')", "0",
        parameters={"variable": "x", "order": 1})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_unresolved_symbolic_comparison_is_unverified():
    graph, edge = _graph_edge("sin(x)", "Abs(x)/x", parameters={"variable": "x", "order": 1})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed

def test_order_is_not_artificially_capped():
    graph, edge = _graph_edge("x**12", "479001600", parameters={"variable": "x", "order": 12})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
