import sympy as sp
import pytest

from automate import calculate, calculate_request, calculator_manifest
from automate.calculator import CalculatorError


def test_ode_solve_first_order_symbolic_equation():
    result = calculate_request({
        "operation": "ode_solve",
        "expression": "diff(y(x), x) = y(x)",
        "dependent_variable": "y",
        "independent_variable": "x",
    })
    x = sp.Symbol("x")
    y = sp.Function("y")
    assert result.lhs == y(x)
    assert sp.simplify(result.rhs.diff(x) - result.rhs) == 0


def test_ode_solve_second_order_equation():
    result = calculate(
        "ode_solve",
        "diff(y(x), x, 2) + y(x) = 0",
        dependent_variable="y",
        independent_variable="x",
    )
    x = sp.Symbol("x")
    y = sp.Function("y")
    assert result.lhs == y(x)
    assert sp.simplify(result.rhs.diff(x, 2) + result.rhs) == 0


def test_ode_solve_supports_explicit_sympy_hint():
    result = calculate_request({
        "operation": "ode_solve",
        "expression": "diff(y(x), x) - y(x)",
        "dependent_variable": "y",
        "independent_variable": "x",
        "hint": "separable",
    })
    assert result.lhs == sp.Function("y")(sp.Symbol("x"))


def test_ode_solve_requires_both_variable_names():
    with pytest.raises(CalculatorError, match="dependent_variable"):
        calculate("ode_solve", "diff(y(x), x) - y(x)", independent_variable="x")


def test_manifest_exposes_ode_solver_arguments():
    operation = {
        item["name"]: item for item in calculator_manifest()["operations"]
    }["ode_solve"]
    assert operation["required"] == [
        "expression", "dependent_variable", "independent_variable"
    ]
    assert "hint" in operation["optional"]
