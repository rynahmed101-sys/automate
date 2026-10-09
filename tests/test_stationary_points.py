import sympy as sp
import pytest

from automate import calculate_request, calculator_manifest
from automate.calculator import CalculatorError


def test_stationary_points_finds_univariate_critical_candidate():
    result = calculate_request({
        "operation": "stationary_points",
        "expression": "(x-2)**2 + 3",
        "variables": ["x"],
    })
    assert result == [{sp.Symbol("x"): 2}]


def test_stationary_points_finds_multivariable_candidate():
    result = calculate_request({
        "operation": "stationary_points",
        "expression": "(x-1)**2 + (y+2)**2",
        "variables": ["x", "y"],
    })
    assert result == [{sp.Symbol("x"): 1, sp.Symbol("y"): -2}]


def test_stationary_points_does_not_claim_extremum_classification():
    operation = {
        item["name"]: item for item in calculator_manifest()["operations"]
    }["stationary_points"]
    assert "does not classify minima or maxima" in operation["description"]


def test_stationary_points_rejects_duplicate_variables():
    with pytest.raises(CalculatorError, match="unique"):
        calculate_request({
            "operation": "stationary_points",
            "expression": "x**2",
            "variables": ["x", "x"],
        })


def test_stationary_points_requires_variables():
    with pytest.raises(CalculatorError, match="requires variables"):
        calculate_request({
            "operation": "stationary_points",
            "expression": "x**2",
        })

def test_stationary_points_rejects_non_finite_stationary_set():
    with pytest.raises(CalculatorError, match="not a finite list"):
        calculate_request({
            "operation": "stationary_points",
            "expression": "7",
            "variables": ["x"],
        })


def test_stationary_points_rejects_expression_independent_of_requested_variables():
    with pytest.raises(CalculatorError, match="not a finite list"):
        calculate_request({
            "operation": "stationary_points",
            "expression": "y**2",
            "variables": ["x"],
        })
