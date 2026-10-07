from types import SimpleNamespace

from automate.backend.sympy_backend import SymPyChecker
from automate.core.status import VerificationStatus


def node(expr: str):
    return SimpleNamespace(expression=SimpleNamespace(raw_str=expr))


def run(params, expression, claimed):
    return SymPyChecker._verify_series_expansion(node(expression), node(claimed), params)


def test_maclaurin_exponential():
    passed, details, evidence, error = run({"variable": "x", "center": "0", "order": 4}, "exp(x)", "1 + x + x**2/2 + x**3/6 + x**4/24")
    assert passed is True
    assert details["order"] == 4
    assert evidence
    assert error is None


def test_taylor_sine_at_nonzero_center():
    passed, details, _, error = run({"variable": "x", "center": "pi/2", "order": 3}, "sin(x)", "1 - (x-pi/2)**2/2")
    assert passed is True
    assert details["order"] == 3
    assert error is None


def test_higher_order_expansion_is_general():
    passed, details, _, error = run({"variable": "x", "center": "1", "order": 6}, "log(x)", "(x-1) - (x-1)**2/2 + (x-1)**3/3 - (x-1)**4/4 + (x-1)**5/5 - (x-1)**6/6")
    assert passed is True
    assert len(details["coefficients"]) == 7
    assert error is None


def test_incorrect_series_is_rejected():
    passed, details, evidence, error = run({"variable": "x", "center": "0", "order": 3}, "exp(x)", "1 + x + x**2/2")
    assert passed is False
    assert details["residual"] != "0"
    assert evidence


def test_zero_order_is_supported():
    passed, _, _, error = run({"variable": "x", "center": "2", "order": 0}, "x**2 + x", "6")
    assert passed is True
    assert error is None


def test_malformed_order_fails_closed():
    passed, _, _, error = run({"variable": "x", "center": "0", "order": -1}, "exp(x)", "1")
    assert passed is False
    assert "non-negative integer" in error


def test_malformed_variable_fails_closed():
    passed, _, _, error = run({"variable": "x+y", "center": "0", "order": 2}, "exp(x)", "1 + x + x**2/2")
    assert passed is False
    assert "valid identifier" in error


def test_nonanalytic_center_fails_closed():
    passed, details, _, error = run({"variable": "x", "center": "0", "order": 3}, "log(x)", "1 + x + x**2/2 + x**3/3")
    assert passed is False
    assert details.get("_status_override") == VerificationStatus.UNVERIFIED.value
    assert "UNVERIFIED" in error


def test_series_rule_is_registered():
    from automate.theory.rules import RuleRegistry
    rule = RuleRegistry().get("series_expansion")
    assert rule is not None
    assert rule.allowed_checkers == ["sympy"]


def test_series_cross_check_is_recorded():
    passed, details, _, error = run({"variable": "x", "center": "0", "order": 5}, "cos(x)", "1 - x**2/2 + x**4/24")
    assert passed is True
    assert details["construction_cross_check"] == "0"
    assert error is None
