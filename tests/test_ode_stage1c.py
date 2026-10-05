import pytest

from automate.ode import ODEEngine
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph_edge(rule, equation, candidate, params=None):
    graph = DerivationGraph(id=f"g_{rule}")
    graph.add_node(DerivationNode(
        id="ode",
        expression=MathematicalExpression(raw_str=equation),
        node_kind="equation",
    ))
    graph.add_node(DerivationNode(
        id="solution",
        expression=MathematicalExpression(raw_str=candidate),
        node_kind="expression",
    ))
    edge = DerivationEdge(
        id=f"edge_{rule}",
        input_nodes=["ode"],
        output_nodes=["solution"],
        transformation_rule=rule,
        justification="Stage 1C ODE verification",
        parameters=params or {},
    )
    graph.add_edge(edge)
    return graph, edge


def test_generic_ode_verifier_supports_arbitrary_order():
    engine = ODEEngine("t", "y")
    result = engine.verify_solution(
        "diff(y(t), t, 4) - y(t) = 0",
        "exp(t)",
    )
    assert result.passed is True
    assert result.status == "SYMBOLIC_CHECKED"
    assert result.details["order"] == 4


def test_generic_ode_rejects_wrong_solution():
    engine = ODEEngine("t", "y")
    result = engine.verify_solution(
        "diff(y(t), t, 3) - y(t) = 0",
        "t**2",
    )
    assert result.passed is False
    assert result.status == "FAILED"
    assert result.details["residual"] != "0"


def test_generic_ode_parser_rejects_adversarial_candidate():
    engine = ODEEngine("t", "y")
    result = engine.verify_solution(
        "diff(y(t), t) = y(t)",
        "__import__('os').system('echo bad')",
    )
    assert result.passed is False
    assert result.status == "FAILED"


def test_separable_equation_and_candidate_are_verified():
    engine = ODEEngine("t", "y")
    result = engine.verify_separable(
        "diff(y(t), t) = t*y(t)",
        "exp(t**2/2)",
        {"f": "t", "g": "y(t)"},
    )
    assert result.passed is True
    assert result.details["factorization_verified"] is True


def test_separable_wrong_factorization_fails_closed():
    engine = ODEEngine("t", "y")
    result = engine.verify_separable(
        "diff(y(t), t) = t*y(t)",
        "exp(t**2/2)",
        {"f": "1", "g": "y(t)"},
    )
    assert result.passed is False


def test_linear_first_order_uses_integrating_factor():
    engine = ODEEngine("t", "y")
    result = engine.verify_linear_first_order(
        "diff(y(t), t) - y(t) = 0",
        "exp(t)",
        {"P": "-1", "Q": "0"},
    )
    assert result.passed is True
    assert "integrating_factor" in result.details


def test_bernoulli_transformation_is_explicitly_verified():
    engine = ODEEngine("t", "y")
    result = engine.verify_bernoulli(
        "diff(y(t), t) + y(t) = y(t)**2",
        "1",
        {"P": "1", "Q": "1", "n": "2"},
    )
    assert result.passed is True
    assert "transformation" in result.details
    assert result.details["nonzero_y_required"] is True


def test_bernoulli_exceptional_n_is_not_silently_treated_as_bernoulli():
    engine = ODEEngine("t", "y")
    result = engine.verify_bernoulli(
        "diff(y(t), t) + y(t) = 0",
        "exp(-t)",
        {"P": "1", "Q": "0", "n": "1"},
    )
    assert result.passed is False


def test_exact_ode_checks_exactness_and_candidate_potential():
    engine = ODEEngine("t", "y")
    result = engine.verify_exact(
        "0",
        "x**2/2 + y**2/2",
        {"x": "x", "y": "y", "M": "x", "N": "y"},
    )
    assert result.passed is True
    assert result.details["exactness_verified"] is True


def test_exact_ode_rejects_non_exact_form():
    engine = ODEEngine("t", "y")
    result = engine.verify_exact(
        "0",
        "x**2/2 + x*y",
        {"x": "x", "y": "y", "M": "y", "N": "y"},
    )
    assert result.passed is False


@pytest.mark.parametrize(
    "equation,candidate,expected_order,root_flags",
    [
        ("diff(y(t),t,2) + 2*diff(y(t),t) + y(t) = 0",
         "(C1 + C2*t)*exp(-t)", 2, ("repeated_roots_present", True)),
        ("diff(y(t),t,2) + 4*y(t) = 0",
         "C1*cos(2*t) + C2*sin(2*t)", 2, ("complex_roots_present", True)),
    ],
)
def test_constant_coefficient_root_families(equation, candidate, expected_order, root_flags):
    engine = ODEEngine("t", "y")
    result = engine.verify_constant_coefficient(equation, candidate, {})
    assert result.passed is True
    assert result.details["order"] == expected_order
    assert result.details[root_flags[0]] is root_flags[1]
    assert result.details["homogeneous_basis"]


def test_constant_coefficient_rejects_forced_equation():
    engine = ODEEngine("t", "y")
    result = engine.verify_constant_coefficient(
        "diff(y(t),t,2) + y(t) = sin(t)",
        "C1*cos(t) + C2*sin(t)",
        {},
    )
    assert result.passed is False


def test_ivp_requires_ode_and_initial_conditions():
    engine = ODEEngine("t", "y")
    result = engine.verify_ivp(
        "diff(y(t),t) - y(t) = 0",
        "exp(t)",
        {"initial_conditions": ["y(0) = 1"]},
    )
    assert result.passed is True
    assert result.details["initial_conditions"][0]["satisfied"] is True


def test_ivp_rejects_condition_violation():
    engine = ODEEngine("t", "y")
    result = engine.verify_ivp(
        "diff(y(t),t) - y(t) = 0",
        "2*exp(t)",
        {"initial_conditions": ["y(0) = 1"]},
    )
    assert result.passed is False


def test_bvp_verifies_both_boundary_conditions():
    engine = ODEEngine("t", "y")
    result = engine.verify_bvp(
        "diff(y(t),t,2) + y(t) = 0",
        "sin(t)",
        {"boundary_conditions": ["y(0) = 0", "y(pi/2) = 1"]},
    )
    assert result.passed is True


def test_bvp_does_not_accept_wrong_boundary_values():
    engine = ODEEngine("t", "y")
    result = engine.verify_bvp(
        "diff(y(t),t,2) + y(t) = 0",
        "cos(t)",
        {"boundary_conditions": ["y(0) = 0", "y(pi/2) = 1"]},
    )
    assert result.passed is False


def test_coupled_system_verification():
    engine = ODEEngine("t", "y")
    result = engine.verify_system(
        "(diff(x(t),t) - y(t), diff(y(t),t) + x(t))",
        "(cos(t), -sin(t))",
        {"functions": ["x", "y"]},
    )
    assert result.passed is True
    assert result.details["equation_count"] == 2


def test_coupled_system_rejects_wrong_component():
    engine = ODEEngine("t", "y")
    result = engine.verify_system(
        "(diff(x(t),t) - y(t), diff(y(t),t) + x(t))",
        "(cos(t), sin(t))",
        {"functions": ["x", "y"]},
    )
    assert result.passed is False


def test_phase_space_conversion_is_order_generic():
    engine = ODEEngine("t", "y")
    result = engine.phase_space(
        "diff(y(t),t,3) + 2*diff(y(t),t) + y(t) = 0",
        "(z1, z2, -2*z1-z0)",
        {"state_variables": ["z0", "z1", "z2"]},
    )
    assert result.passed is True
    assert result.details["order"] == 3


def test_phase_space_rejects_wrong_state_system():
    engine = ODEEngine("t", "y")
    result = engine.phase_space(
        "diff(y(t),t,2) + y(t) = 0",
        "(z1, z0)",
        {"state_variables": ["z0", "z1"]},
    )
    assert result.passed is False


def test_backend_routes_new_ode_rule_and_preserves_unverified_status():
    graph, edge = _graph_edge(
        "verify_ode_solution",
        "diff(y(t),t) = y(t)",
        "exp(t)",
        {"variable": "t", "function": "y"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED

    graph, edge = _graph_edge(
        "verify_ode_solution",
        "diff(y(t),t) = a*y(t)",
        "exp(a*t)",
        {"variable": "t", "function": "y"},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status in {VerificationStatus.SYMBOLIC_CHECKED, VerificationStatus.UNVERIFIED}


def test_backend_routes_ivp_rule():
    graph, edge = _graph_edge(
        "verify_ode_ivp",
        "diff(y(t),t) = y(t)",
        "exp(t)",
        {"initial_conditions": ["y(0)=1"]},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
