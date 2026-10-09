import sympy as sp
import pytest

from automate import calculate_request, calculator_manifest
from automate.calculator import CalculatorError


def test_laplace_transform():
    result = calculate_request({
        "operation": "transform",
        "expression": "exp(2*t)",
        "variable": "t",
        "transform_type": "laplace",
        "transform_variable": "s",
    })
    s = sp.Symbol("s")
    assert sp.simplify(result - 1 / (s - 2)) == 0


def test_inverse_laplace_transform():
    result = calculate_request({
        "operation": "transform",
        "expression": "1/(s-2)",
        "variable": "s",
        "transform_type": "laplace",
        "transform_variable": "t",
        "inverse": True,
    })
    t = sp.Symbol("t")
    expected = sp.exp(2*t) * sp.Heaviside(t)
    assert sp.simplify(result - expected) == 0


def test_fourier_transform_and_inverse():
    forward = calculate_request({
        "operation": "transform",
        "expression": "exp(-x**2)",
        "variable": "x",
        "transform_type": "fourier",
        "transform_variable": "k",
    })
    k = sp.Symbol("k")
    assert sp.simplify(forward - sp.sqrt(sp.pi)*sp.exp(-sp.pi**2*k**2)) == 0

    inverse = calculate_request({
        "operation": "transform",
        "expression": str(forward),
        "variable": "k",
        "transform_type": "fourier",
        "transform_variable": "x",
        "inverse": True,
    })
    x = sp.Symbol("x")
    assert sp.simplify(inverse - sp.exp(-x**2)) == 0


def test_transform_rejects_unknown_type():
    with pytest.raises(CalculatorError, match="transform_type"):
        calculate_request({
            "operation": "transform",
            "expression": "exp(-x**2)",
            "variable": "x",
            "transform_type": "z",
            "transform_variable": "z",
        })


def test_manifest_documents_transform_contract():
    operation = {
        item["name"]: item for item in calculator_manifest()["operations"]
    }["transform"]
    assert operation["required"] == ["expression", "transform_type", "transform_variable"]
    assert operation["optional"] == ["variable", "inverse"]
