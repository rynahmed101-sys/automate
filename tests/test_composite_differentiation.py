"""Focused Stage 1B acceptance campaign for composite and implicit differentiation."""

import pytest
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression

def _edge(rule, output_expr, parameters):
    graph = DerivationGraph(id="composite_derivative_acceptance")
    input_expr = parameters.pop("_input", "0")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=input_expr)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output_expr)))
    edge = DerivationEdge(id="edge", input_nodes=["in"], output_nodes=["out"],
        transformation_rule=rule, justification="Stage 1B composite differentiation campaign",
        checker="sympy", parameters=parameters)
    graph.add_edge(edge)
    return graph, edge

@pytest.mark.parametrize("rule,output,params", [
    ("chain_rule", "cos(x**2)*2*x", {"variable":"x","outer":"sin(u)","inner":"x**2","inner_variable":"u"}),
    ("product_rule", "2*x*exp(x) + x**2*exp(x)", {"variable":"x","factors":["x**2","exp(x)"]}),
    ("product_rule", "(2*x + 2)*(x + 1) + (x**2 + 2*x)", {"variable":"x","factors":["x**2 + 2*x","x + 1"]}),
    ("quotient_rule", "((2*x)*(x+1) - (x**2+1))/((x+1)**2)", {"variable":"x","numerator":"x**2+1","denominator":"x+1"}),
])
def test_composite_rules(rule, output, params):
    graph, edge = _edge(rule, output, {**params, "_input":"unused"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED

def test_chain_rule_rejects_wrong_derivative():
    graph, edge = _edge("chain_rule", "cos(x**2)", {"variable":"x","outer":"sin(u)","inner":"x**2","inner_variable":"u","_input":"unused"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_quotient_rule_rejects_identically_zero_denominator():
    graph, edge = _edge("quotient_rule", "0", {"variable":"x","numerator":"x","denominator":"0","_input":"unused"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

@pytest.mark.parametrize("relation,expected", [
    ("x**2 + y**2 - 1", "-x/y"),
    ("x*y + sin(y) - x", "(1-y)/(x+cos(y))"),
])
def test_implicit_differentiation(relation, expected):
    graph, edge = _edge("implicit_differentiate", expected, {
        "independent_variable":"x", "dependent_variable":"y", "_input":relation
    })
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["F_y"] != "0"

def test_implicit_differentiation_rejects_wrong_result():
    graph, edge = _edge("implicit_differentiate", "x/y", {
        "independent_variable":"x", "dependent_variable":"y", "_input":"x**2+y**2-1"
    })
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_implicit_differentiation_fails_closed_when_Fy_identically_zero():
    graph, edge = _edge("implicit_differentiate", "0", {
        "independent_variable":"x", "dependent_variable":"y", "_input":"x**2-1"
    })
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed

@pytest.mark.parametrize("params", [
    {"variable":"x","outer":"sin(u)","inner":"x**2"},
    {"variable":"x","factors":["x"]},
    {"variable":"x","numerator":"x","denominator":"0"},
])
def test_composite_malformed_inputs_fail_closed(params):
    rule = "chain_rule" if "outer" in params else ("product_rule" if "factors" in params else "quotient_rule")
    graph, edge = _edge(rule, "0", {**params, "_input":"unused"})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_implicit_malformed_variables_fail_closed():
    graph, edge = _edge("implicit_differentiate", "0", {
        "independent_variable":"x", "dependent_variable":"x", "_input":"x+y"
    })
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed

def test_composite_domain_dependent_wrong_result_is_failed():
    # Abs(x)/x is not equal to the chain-rule derivative 1/x without an
    # explicit domain assumption. This is a demonstrably false claim, not
    # an unresolved symbolic comparison, so the checker should reject it.
    graph, edge = _edge("chain_rule", "Abs(x)/x", {
        "variable":"x","outer":"log(u)","inner":"x","inner_variable":"u","_input":"unused"
    })
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed
