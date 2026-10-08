"""Acceptance tests for Stage 1B partial derivatives and total differentials."""

from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _edge(rule, source, target, parameters):
    graph = DerivationGraph(id="multivariable_calculus")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=source)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=target)))
    edge = DerivationEdge(id="edge", input_nodes=["in"], output_nodes=["out"], transformation_rule=rule,
                          justification="Stage 1B acceptance test", checker="sympy", parameters=parameters)
    graph.add_edge(edge)
    return graph, edge


def test_partial_derivative_is_verified_with_explicit_variable():
    graph, edge = _edge("partial_differentiate", "x**2*y + sin(x*y)", "2*x*y + y*cos(x*y)", {"variable": "x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["derivative_kind"] == "partial"
    assert report.details["variable"] == "x"


def test_partial_derivative_wrong_variable_is_rejected():
    graph, edge = _edge("partial_differentiate", "x**2*y + sin(x*y)", "2*x*y + y*cos(x*y)", {"variable": "y"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_total_differential_is_verified():
    graph, edge = _edge("total_differential", "x**2*y + sin(x*y)",
                        "dx*(2*x*y + y*cos(x*y)) + dy*(x**2 + x*cos(x*y))",
                        {"variables": ["x", "y"], "differentials": ["dx", "dy"]})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["partial_derivatives"]["x"] == "2*x*y + y*cos(x*y)"


def test_total_differential_malformed_variables_fail_closed():
    graph, edge = _edge("total_differential", "x*y", "y*dx + x*dy", {"variables": "x,y"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_partial_derivative_unsafe_expression_fails_closed():
    graph, edge = _edge("partial_differentiate", "__import__('os').system('bad')", "0", {"variable": "x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_total_differential_variable_and_differential_collision_fails_closed():
    graph, edge = _edge("total_differential", "x*y", "x*(y) + y*(x)", {"variables": ["x", "y"], "differentials": ["x", "dy"]})
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED
