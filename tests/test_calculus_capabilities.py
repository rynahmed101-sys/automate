import sympy as sp
import pytest

from automate import CALCULATOR_OPERATIONS, calculate, calculate_request, calculator_manifest
from automate.calculator import CalculatorError


def test_nth_derivative():
    assert calculate("differentiate", "x**4", variable="x", derivative_order=3) == 24 * sp.Symbol("x")


def test_definite_integral_uses_both_bounds():
    assert calculate_request({
        "operation": "integrate_definite",
        "expression": "x**2",
        "variable": "x",
        "lower": "0",
        "upper": "3",
    }) == 9


def test_limit_direction_is_exposed():
    assert calculate_request({
        "operation": "limit",
        "expression": "1/x",
        "variable": "x",
        "point": "0",
        "direction": "+",
    }) == sp.oo
    assert calculate_request({
        "operation": "limit",
        "expression": "1/x",
        "variable": "x",
        "point": "0",
        "direction": "-",
    }) == -sp.oo


def test_series_can_expand_around_nonzero_point():
    x = sp.Symbol("x")
    result = calculate_request({
        "operation": "series",
        "expression": "exp(x)",
        "variable": "x",
        "point": "1",
        "order": 3,
    })
    assert sp.simplify(result.removeO() - (sp.E + sp.E*(x - 1) + sp.E*(x - 1)**2/2)) == 0
    assert result.getO() is not None


def test_solve_system_accepts_more_than_two_equations():
    result = calculate_request({
        "operation": "solve_system",
        "expression": "x + y + z - 6",
        "equations": ["x - 1", "y - 2", "z - 3"],
        "variables": ["x", "y", "z"],
    })
    assert result == {sp.Symbol("x"): 1, sp.Symbol("y"): 2, sp.Symbol("z"): 3}


def test_solve_system_keeps_two_equation_compatibility():
    result = calculate(
        "solve_system", "x + y - 3",
        second_expression="x - y - 1",
        variables=["x", "y"],
    )
    assert result == {sp.Symbol("x"): 2, sp.Symbol("y"): 1}


def test_manifest_documents_new_calculus_arguments():
    manifest = calculator_manifest()
    by_name = {item["name"]: item for item in manifest["operations"]}
    assert "integrate_definite" in CALCULATOR_OPERATIONS
    assert by_name["integrate_definite"]["required"] == ["expression", "lower", "upper"]
    assert "direction" in by_name["limit"]["optional"]
    assert "equations" in by_name["solve_system"]["optional"]


def test_definite_integral_rejects_missing_bounds():
    with pytest.raises(CalculatorError, match="lower and upper"):
        calculate("integrate_definite", "x**2", variable="x", lower="0")
