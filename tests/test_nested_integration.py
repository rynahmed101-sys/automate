"""Focused Stage 1B acceptance campaign for repeated and nested integration."""

import pytest
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression

def _edge(integrand, result, variables):
    graph = DerivationGraph(id="nested_integration_acceptance")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=integrand)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=result)))
    edge = DerivationEdge(id="edge", input_nodes=["in"], output_nodes=["out"],
        transformation_rule="nested_integrate", justification="Stage 1B nested integration campaign",
        checker="sympy", parameters={"variables": variables})
    graph.add_edge(edge)
    return graph, edge

@pytest.mark.parametrize("integrand,result,variables", [
    ("x", "x**3/6", ["x", "x"]),
    ("x*y", "x**2*y**2/4", ["x", "y"]),
    ("sin(x)", "-sin(x)", ["x", "x"]),
])
def test_nested_indefinite_integration(integrand, result, variables):
    graph, edge = _edge(integrand, result, variables)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["integration_depth"] == len(variables)

def test_mixed_variable_order_is_explicit():
    graph, edge = _edge("x + y", "x**2*y/2 + x*y**2/2", ["x", "y"])
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["variables"] == ["x", "y"]

def test_rejects_wrong_nested_integral():
    graph, edge = _edge("x", "x**2/2", ["x", "x"])
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

@pytest.mark.parametrize("variables", [
    [],
    ["x", ""],
    ["x", "not-valid"],
])
def test_malformed_nested_variable_sequence_fails_closed(variables):
    graph, edge = _edge("x", "x", variables)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_very_deep_repeated_integration_has_no_small_order_ceiling():
    variables = ["x"] * 6
    graph, edge = _edge("x", "x**7/5040", variables)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message

def test_unresolved_nested_integral_is_unverified():
    graph, edge = _edge("x**x", "x", ["x", "x"])
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed
