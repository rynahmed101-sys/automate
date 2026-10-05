"""Stage 1B acceptance campaign for explicit integration techniques."""

import pytest

from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _edge(rule, integrand, result, parameters):
    graph = DerivationGraph(id=f"{rule}_acceptance")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=integrand)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=result)))
    edge = DerivationEdge(
        id="edge",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Stage 1B integration-technique acceptance campaign",
        checker="sympy",
        parameters=parameters,
    )
    graph.add_edge(edge)
    return graph, edge


def _report(rule, integrand, result, parameters):
    graph, edge = _edge(rule, integrand, result, parameters)
    return SymPyChecker().verify_edge(edge, graph)


@pytest.mark.parametrize(
    "integrand,result,params",
    [
        (
            "2*x*cos(x**2)",
            "sin(x**2)",
            {
                "variable": "x",
                "substitution_variable": "u",
                "substitution_expression": "x**2",
                "transformed_integrand": "cos(u)",
            },
        ),
        (
            "2*x/(1+x**2)",
            "log(1+x**2)",
            {
                "variable": "x",
                "substitution_variable": "u",
                "substitution_expression": "1+x**2",
                "transformed_integrand": "1/u",
            },
        ),
    ],
)
def test_integration_by_substitution_positive(integrand, result, params):
    report = _report("integration_by_substitution", integrand, result, params)
    assert report.passed, report.error_message
    assert report.details["du_dx"]


def test_substitution_missing_jacobian_is_rejected():
    report = _report(
        "integration_by_substitution",
        "2*x*cos(x**2)",
        "sin(x**2)",
        {
            "variable": "x",
            "substitution_variable": "u",
            "substitution_expression": "x**2",
            "transformed_integrand": "2*cos(u)",
        },
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_substitution_zero_jacobian_fails_closed():
    report = _report(
        "integration_by_substitution",
        "x",
        "x**2/2",
        {
            "variable": "x",
            "substitution_variable": "u",
            "substitution_expression": "3",
            "transformed_integrand": "x",
        },
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_substitution_malformed_payload_fails_closed():
    report = _report(
        "integration_by_substitution",
        "2*x",
        "x**2",
        {"variable": "x", "substitution_expression": "x**2"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


@pytest.mark.parametrize(
    "integrand,result,params",
    [
        (
            "x*exp(x)",
            "x*exp(x)-exp(x)",
            {"variable": "x", "u": "x", "dv": "exp(x)", "v": "exp(x)"},
        ),
        (
            "x*cos(x)",
            "x*sin(x)+cos(x)",
            {"variable": "x", "u": "x", "dv": "cos(x)", "v": "sin(x)"},
        ),
    ],
)
def test_integration_by_parts_positive(integrand, result, params):
    report = _report("integration_by_parts", integrand, result, params)
    assert report.passed, report.error_message
    assert report.details["parts_result"]


def test_integration_by_parts_wrong_v_is_rejected():
    report = _report(
        "integration_by_parts",
        "x*exp(x)",
        "x*exp(x)-exp(x)",
        {"variable": "x", "u": "x", "dv": "exp(x)", "v": "exp(x)+1"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_integration_by_parts_malformed_payload_fails_closed():
    report = _report(
        "integration_by_parts",
        "x*exp(x)",
        "x*exp(x)-exp(x)",
        {"variable": "x", "u": "x", "dv": "exp(x)"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_integration_by_parts_unresolved_remainder_is_unverified():
    report = _report(
        "integration_by_parts",
        "x*x**x*(log(x)+1)",
        "x*x**x-x**x",
        {
            "variable": "x",
            "u": "x",
            "dv": "x**x*(log(x)+1)",
            "v": "x**x",
        },
    )
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


@pytest.mark.parametrize(
    "integrand,decomposition,result",
    [
        (
            "1/((x+1)*(x+2))",
            "1/(x+1)-1/(x+2)",
            "log(x+1)-log(x+2)",
        ),
        (
            "1/(x-1)**2",
            "1/(x-1)**2",
            "-1/(x-1)",
        ),
        (
            "x/(x**2+1)",
            "x/(x**2+1)",
            "log(x**2+1)/2",
        ),
    ],
)
def test_partial_fractions_positive(integrand, decomposition, result):
    report = _report(
        "partial_fractions_integrate",
        integrand,
        result,
        {"variable": "x", "decomposition": decomposition},
    )
    assert report.passed, report.error_message
    assert "!=" in report.details["domain_restriction"]


def test_partial_fractions_wrong_decomposition_is_rejected():
    report = _report(
        "partial_fractions_integrate",
        "1/((x+1)*(x+2))",
        "1/(x+1)+1/(x+2)",
        "0",
    )
    # Preserve fail-closed behavior even for malformed parameter types.
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_partial_fractions_singular_denominator_is_rejected():
    report = _report(
        "partial_fractions_integrate",
        "1/(x-x)",
        "1/(x-x)",
        {"variable": "x", "decomposition": "1/(x-x)"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_partial_fractions_malformed_payload_fails_closed():
    report = _report(
        "partial_fractions_integrate",
        "1/(x+1)",
        "log(x+1)",
        {"variable": "x"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


@pytest.mark.parametrize(
    "integrand,result",
    [
        ("sin(x)**3", "-cos(x)+cos(x)**3/3"),
        ("x*sin(x)", "-x*cos(x)+sin(x)"),
        ("cos(x)**4", "3*x/8+sin(2*x)/4+sin(4*x)/32"),
    ],
)
def test_trigonometric_integration_positive(integrand, result):
    report = _report(
        "trigonometric_integrate",
        integrand,
        result,
        {"variable": "x"},
    )
    assert report.passed, report.error_message
    assert report.details["method"] == "sympy.manualintegrate"


def test_trigonometric_wrong_candidate_is_rejected():
    report = _report(
        "trigonometric_integrate",
        "sin(x)**3",
        "cos(x)",
        {"variable": "x"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_trigonometric_non_trig_input_fails_closed():
    report = _report(
        "trigonometric_integrate",
        "x**2",
        "x**3/3",
        {"variable": "x"},
    )
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_trigonometric_unresolved_case_is_unverified():
    report = _report(
        "trigonometric_integrate",
        "sin(x)**x",
        "0",
        {"variable": "x"},
    )
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


def test_all_new_rules_reject_adversarial_parser_input():
    cases = [
        (
            "integration_by_substitution",
            "__import__('os').system('echo bad')",
            "0",
            {
                "variable": "x",
                "substitution_variable": "u",
                "substitution_expression": "x",
                "transformed_integrand": "0",
            },
        ),
        (
            "integration_by_parts",
            "__import__('os').system('echo bad')",
            "0",
            {"variable": "x", "u": "x", "dv": "1", "v": "x"},
        ),
        (
            "partial_fractions_integrate",
            "__import__('os').system('echo bad')",
            "0",
            {"variable": "x", "decomposition": "0"},
        ),
        (
            "trigonometric_integrate",
            "__import__('os').system('echo bad')",
            "0",
            {"variable": "x"},
        ),
    ]
    for rule, integrand, result, params in cases:
        report = _report(rule, integrand, result, params)
        assert report.status == VerificationStatus.FAILED
        assert not report.passed
