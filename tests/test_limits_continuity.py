import pytest
import sympy as sp

from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph_edge(rule, input_expr, output_expr, *, parameters=None):
    graph = DerivationGraph(id=f"limits_{rule}")
    graph.add_node(DerivationNode(
        id="in",
        expression=MathematicalExpression(raw_str=input_expr),
    ))
    graph.add_node(DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str=output_expr),
    ))
    edge = DerivationEdge(
        id="edge",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Stage 1B limits and continuity acceptance campaign",
        checker="sympy",
        parameters=parameters or {},
    )
    graph.add_edge(edge)
    return graph, edge


@pytest.mark.parametrize(
    "expr,target,expected",
    [
        ("(x**2-a**2)/(x-a)", "0", "a"),
        ("sin(x)/x", "0", "1"),
        ("x**2 + 3*x + 1", "2", "11"),
    ],
)
def test_finite_two_sided_limits(expr, target, expected):
    graph, edge = _graph_edge("limit", expr, expected,
                              parameters={"variable": "x", "point": target, "direction": "two_sided", "assumptions": {"a": "real"}})
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED


def test_removable_discontinuity_limit_exists_even_when_value_is_undefined():
    graph, edge = _graph_edge(
        "limit", "(x**2-1)/(x-1)", "2",
        parameters={"variable": "x", "point": "1", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    assert report.details["computed_limit"] == "2"


@pytest.mark.parametrize(
    "direction,expected",
    [("left", "-oo"), ("right", "oo")],
)
def test_one_sided_limits_preserve_direction(direction, expected):
    graph, edge = _graph_edge(
        "limit", "1/x", expected,
        parameters={"variable": "x", "point": "0", "direction": direction},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["direction"] == direction


def test_unequal_one_sided_limits_make_two_sided_limit_nonexistent():
    graph, edge = _graph_edge(
        "limit", "1/x", "DNE",
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    assert report.details["existence_class"] == "nonexistent"


def test_oscillatory_limit_is_not_declared_finite():
    graph, edge = _graph_edge(
        "limit", "sin(1/x)", "DNE",
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    assert report.details["existence_class"] == "nonexistent"


@pytest.mark.parametrize(
    "expr,point,expected,direction",
    [
        ("x/(x+1)", "oo", "1", "+infinity"),
        ("x/(x+1)", "-oo", "1", "-infinity"),
        ("1/x", "oo", "0", "+infinity"),
        ("1/x", "-oo", "0", "-infinity"),
    ],
)
def test_limits_at_infinity(expr, point, expected, direction):
    graph, edge = _graph_edge(
        "limit", expr, expected,
        parameters={"variable": "x", "point": point, "direction": direction},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["direction"] == direction


def test_continuity_is_built_from_limit_and_function_value():
    graph, edge = _graph_edge(
        "continuity", "x**2+1", "1",
        parameters={"variable": "x", "point": "2", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["continuous_indicator"] == 1
    assert report.details["function_value"] == "5"
    assert report.details["two_sided_limit"] == "5"


def test_removable_discontinuity_is_not_continuous_because_function_value_is_undefined():
    graph, edge = _graph_edge(
        "continuity", "(x**2-1)/(x-1)", "0",
        parameters={"variable": "x", "point": "1", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    assert report.details["function_value_defined"] is False


def test_jump_discontinuity_is_not_continuous():
    graph, edge = _graph_edge(
        "continuity", "Abs(x)/x", "0",
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    assert report.details["continuous_indicator"] == 0


def test_real_domain_is_respected_for_two_sided_limits():
    graph, edge = _graph_edge(
        "limit", "sqrt(x)", "0",
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


def test_symbolic_parameter_and_assumption():
    graph, edge = _graph_edge(
        "limit", "sin(a*x)/x", "a",
        parameters={
            "variable": "x",
            "point": "0",
            "direction": "two_sided",
            "assumptions": {"a": ["positive", "real"]},
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.details["computed_limit"] == "a"


def test_symbolic_target_without_real_assumption_fails_closed():
    graph, edge = _graph_edge(
        "limit", "sqrt(x)", "0",
        parameters={"variable": "x", "point": "a", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("x**2", "3"),
        ("1/x", "0"),
    ],
)
def test_wrong_limit_claim_rejected(expr, expected):
    graph, edge = _graph_edge(
        "limit", expr, expected,
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"variable": "x", "point": "0", "direction": "sideways"},
        {"variable": "x", "direction": "two_sided"},
        {"variable": "x", "point": "0", "direction": "two_sided", "assumptions": {"bad-name": "real"}},
    ],
)
def test_malformed_limit_parameters_fail_closed(parameters):
    graph, edge = _graph_edge("limit", "x", "0", parameters=parameters)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_malicious_expression_is_rejected_by_safe_parser():
    graph, edge = _graph_edge(
        "limit", "__import__('os').system('echo bad')", "0",
        parameters={"variable": "x", "point": "0"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_numerical_evidence_is_independent_and_not_the_proof():
    graph, edge = _graph_edge(
        "limit", "(x**2-1)/(x-1)", "2",
        parameters={"variable": "x", "point": "1", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed
    evidence = report.details["numeric_evidence"]
    assert evidence["independence_class"] == "DIFFERENT_ENGINE"
    assert evidence["evidence_only"] is True


def test_unsupported_output_marker_is_rejected():
    graph, edge = _graph_edge(
        "limit", "x", "x***2",
        parameters={"variable": "x", "point": "0", "direction": "two_sided"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_continuity_requires_two_sided_finite_point():
    graph, edge = _graph_edge(
        "continuity", "x", "1",
        parameters={"variable": "x", "point": "oo", "direction": "+infinity"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed
