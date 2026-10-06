from types import SimpleNamespace

from automate.backend.sympy_backend import SymPyChecker
from automate.core.status import VerificationStatus


def node(expr: str):
    return SimpleNamespace(expression=SimpleNamespace(raw_str=expr))


def run(params, integrand, claimed):
    return SymPyChecker._verify_improper_integral(
        node(integrand),
        node(claimed),
        params,
    )


def test_infinite_upper_bound_converges_and_matches():
    passed, details, _, error = run(
        {"variable": "x", "lower": "1", "upper": "oo"},
        "1/x**2",
        "1",
    )
    assert passed is True
    assert details["converges"] is True
    assert error is None


def test_infinite_upper_bound_diverges():
    passed, details, evidence, error = run(
        {"variable": "x", "lower": "1", "upper": "oo"},
        "1/x",
        "0",
    )
    assert passed is False
    assert details["converges"] is False
    assert "diverg" in error.lower()
    assert evidence


def test_lower_endpoint_singularity_converges():
    passed, details, _, error = run(
        {"variable": "x", "lower": "0", "upper": "1", "endpoint": "lower"},
        "1/sqrt(x)",
        "2",
    )
    assert passed is True
    assert details["converges"] is True
    assert error is None


def test_interior_singularity_diverges():
    passed, details, evidence, error = run(
        {"variable": "x", "lower": "-1", "upper": "1", "singular_point": "0"},
        "1/x**2",
        "0",
    )
    assert passed is False
    assert details["converges"] is False
    assert "diverg" in error.lower()
    assert evidence


def test_finite_bounds_without_improper_marker_fail_closed():
    passed, details, _, error = run(
        {"variable": "x", "lower": "0", "upper": "1"},
        "x",
        "1/2",
    )
    assert passed is False
    assert "singular_point" in error.lower() or "endpoint" in error.lower()


def test_incorrect_convergent_value_is_rejected():
    passed, details, _, error = run(
        {"variable": "x", "lower": "1", "upper": "oo"},
        "1/x**2",
        "2",
    )
    assert passed is False
    assert details["converges"] is True
    assert "incorrect" in error.lower()


def test_two_sided_infinite_integral_requires_both_tails():
    passed, details, _, error = run(
        {"variable": "x", "lower": "-oo", "upper": "oo"},
        "1/(1+x**2)",
        "pi",
    )
    assert passed is True
    assert details["converges"] is True
    assert error is None


def test_two_sided_infinite_integral_diverges_if_one_tail_diverges():
    passed, details, evidence, error = run(
        {"variable": "x", "lower": "-oo", "upper": "oo"},
        "exp(x)",
        "0",
    )
    assert passed is False
    assert details["converges"] is False
    assert evidence
    assert "diverg" in error.lower()


def test_upper_endpoint_singularity_converges():
    passed, details, _, error = run(
        {"variable": "x", "lower": "0", "upper": "1", "endpoint": "upper"},
        "1/sqrt(1-x)",
        "2",
    )
    assert passed is True
    assert details["converges"] is True
    assert error is None


def test_uncertain_symbolic_value_comparison_fails_closed():
    passed, details, evidence, error = run(
        {"variable": "x", "lower": "0", "upper": "oo"},
        "1/(1+x**2)",
        "a",
    )
    assert passed is False
    assert details.get("_status_override") == VerificationStatus.UNVERIFIED.value
    assert evidence == []
    assert "UNVERIFIED" in error


def test_two_sided_inverse_x_never_gets_principal_value_certified():
    passed, details, evidence, error = run(
        {"variable": "x", "lower": "-oo", "upper": "oo"},
        "1/x",
        "0",
    )
    assert passed is False
    assert details.get("converges") is not True
    assert "UNVERIFIED" in (error or "") or "diverg" in (error or "").lower()
