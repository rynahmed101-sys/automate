"""Focused Stage 1B acceptance campaign for symbolic integration."""

import pytest
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression

def _edge(integrand, result, parameters):
    graph = DerivationGraph(id="integration_acceptance")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=integrand)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=result)))
    edge = DerivationEdge(id="edge", input_nodes=["in"], output_nodes=["out"],
        transformation_rule="integrate", justification="Stage 1B integration acceptance campaign",
        checker="sympy", parameters=parameters)
    graph.add_edge(edge)
    return graph, edge

@pytest.mark.parametrize("integrand,result", [
    ("2*x", "x**2"),
    ("sin(x)", "-cos(x)"),
    ("1/x", "log(x)"),
])
def test_indefinite_integration(integrand, result):
    graph, edge = _edge(integrand, result, {"variable":"x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["mode"] == "indefinite"

def test_indefinite_integration_allows_constant_of_integration():
    graph, edge = _edge("2*x", "x**2 + 17", {"variable":"x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message

def test_repeated_indefinite_integration_has_no_artificial_order_ceiling():
    graph, edge = _edge("x", "x**3/6", {"variable":"x", "order":2})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["order"] == 2

@pytest.mark.parametrize("integrand,lower,upper,result", [
    ("x", "0", "1", "1/2"),
    ("sin(x)", "0", "pi", "2"),
    ("1/x", "1", "E", "1"),
])
def test_definite_integration(integrand, lower, upper, result):
    graph, edge = _edge(integrand, result, {"variable":"x","lower":lower,"upper":upper})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["mode"] == "definite"

def test_incorrect_integral_is_rejected():
    graph, edge = _edge("x**2", "x**2", {"variable":"x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_malformed_bounds_fail_closed():
    graph, edge = _edge("x", "x**2/2", {"variable":"x","lower":"0"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_malformed_order_fails_closed():
    graph, edge = _edge("x", "x**2/2", {"variable":"x","order":0})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_unevaluated_symbolic_integral_is_unverified():
    graph, edge = _edge("x**x", "x", {"variable":"x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed

def test_safe_parser_rejects_malicious_integrand():
    graph, edge = _edge("__import__('os').system('echo bad')", "0", {"variable":"x"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed
