import math
import pytest
import sympy as sp

from automate import calculate_request, calculator_manifest
from automate.calculator import CalculatorError


def test_unit_conversion():
    result = calculate_request({
        "operation": "unit_convert",
        "expression": "1",
        "source_unit": "km",
        "target_unit": "m",
    })
    assert math.isclose(float(result.magnitude), 1000.0)
    assert str(result.units) == "meter"


def test_unit_conversion_rejects_incompatible_units():
    with pytest.raises(CalculatorError, match="Could not convert units"):
        calculate_request({
            "operation": "unit_convert",
            "expression": "1",
            "source_unit": "meter",
            "target_unit": "second",
        })


def test_descriptive_statistics_sequence_and_single_sample():
    result = calculate_request({"operation": "descriptive_statistics", "expression": [1, 2, 3, 4]})
    assert result["count"] == 4
    assert result["mean"] == 2.5
    assert result["median"] == 2.5
    assert result["population_variance"] == 1.25
    assert result["sample_variance"] == pytest.approx(5 / 3)
    single = calculate_request({"operation": "descriptive_statistics", "expression": [7]})
    assert single["sample_variance"] is None


def test_descriptive_statistics_rejects_nonfinite_values():
    with pytest.raises(CalculatorError, match="finite data"):
        calculate_request({"operation": "descriptive_statistics", "expression": [1, float("inf")]})


def test_normal_distribution_pdf_and_probability_domain():
    result = calculate_request({
        "operation": "distribution", "expression": "0",
        "distribution_name": "normal", "distribution_function": "pdf",
    })
    assert result == pytest.approx(1 / math.sqrt(2 * math.pi))
    with pytest.raises(CalculatorError, match=r"\[0, 1\]"):
        calculate_request({
            "operation": "distribution", "expression": "2",
            "distribution_name": "normal", "distribution_function": "ppf",
        })


def test_distribution_parameters_are_allowlisted_numeric_values():
    with pytest.raises(CalculatorError, match="finite real numeric"):
        calculate_request({
            "operation": "distribution", "expression": "0",
            "distribution_name": "normal", "distribution_function": "pdf",
            "distribution_parameters": {"loc": float("nan")},
        })


def test_pde_solver_transport_equation():
    result = calculate_request({
        "operation": "pde_solve",
        "expression": "diff(u(x,y), x) + diff(u(x,y), y) = 0",
    })
    x, y = sp.symbols("x y")
    u = sp.Function("u")
    assert result.lhs == u(x, y)
    assert result.rhs == sp.Function("F")(x - y)


def test_stationary_points_reject_partially_free_solution_set():
    with pytest.raises(CalculatorError, match="free requested variables"):
        calculate_request({
            "operation": "stationary_points",
            "expression": "x**2",
            "variables": ["x", "y"],
        })


def test_manifest_exposes_new_operations():
    names = {item["name"] for item in calculator_manifest()["operations"]}
    assert {"unit_convert", "descriptive_statistics", "distribution", "pde_solve"} <= names
