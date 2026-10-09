import json

import sympy as sp
from click.testing import CliRunner

from automate import calculate_request, calculator_manifest, result_data
from automate.cli import main
from automate import CALCULATOR_OPERATIONS
from automate.calculator import CalculatorError


def test_manifest_lists_every_callable_operation():
    manifest = calculator_manifest()
    assert manifest["schema_version"] == "automate.calculator.v1"
    assert {item["name"] for item in manifest["operations"]} == set(CALCULATOR_OPERATIONS)
    assert all(item["description"] and "expression" in item["required"] for item in manifest["operations"])


def test_series_manifest_explains_sympy_order_term():
    series = next(
        item for item in calculator_manifest()["operations"] if item["name"] == "series"
    )
    assert "SymPy's order convention" in series["description"]
    assert "Order term" in series["description"]


def test_structured_request_accepts_native_sympy_objects():
    x = sp.Symbol("x")
    assert calculate_request({"operation": "solve", "expression": x**2 - 4, "variable": "x"}) == [-2, 2]


def test_structured_request_parses_variable_lists_and_rejects_unknown_fields():
    result = calculate_request({
        "operation": "gradient",
        "expression": "x**2 + y**2",
        "variables": "x, y",
    })
    assert result == sp.Matrix([2 * sp.Symbol("x"), 2 * sp.Symbol("y")])
    try:
        calculate_request({"operation": "simplify", "expression": "x", "surprise": True})
    except CalculatorError as exc:
        assert "Unknown request field" in str(exc)
    else:
        raise AssertionError("unknown request fields must fail clearly")


def test_result_data_preserves_matrix_shape_and_entries():
    data = result_data(sp.Matrix([[1, 2], [3, 4]]))
    assert data["type"] == "matrix"
    assert data["shape"] == [2, 2]
    assert data["entries"] == [["1", "2"], ["3", "4"]]


def test_cli_structured_request_returns_typed_json():
    runner = CliRunner()
    result = runner.invoke(main, [
        "request", "--request-json",
        json.dumps({"operation": "matrix_determinant", "expression": "Matrix((1,2),(3,4))"}),
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["result"] == "-2"
    assert payload["result_data"]["type"] == "sympy"


def test_cli_capabilities_include_machine_readable_contract():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["calculator"]["schema_version"] == "automate.calculator.v1"
    assert "matrix_determinant" in {op["name"] for op in payload["calculator"]["operations"]}


def test_multivariable_differential_and_vector_calculus_operations():
    x, y, z = sp.symbols("x y z")
    assert calculate_request({
        "operation": "total_differential",
        "expression": "x**2*y",
        "variables": ["x", "y"],
    }) == 2*x*y*sp.Symbol("d_x") + x**2*sp.Symbol("d_y")
    assert calculate_request({
        "operation": "divergence",
        "expression": "Matrix((x**2, y**2, z**2))",
        "variables": ["x", "y", "z"],
    }) == 2*x + 2*y + 2*z
    assert calculate_request({
        "operation": "curl",
        "expression": "Matrix((y, z, x))",
        "variables": ["x", "y", "z"],
    }) == sp.Matrix([-1, -1, -1])
    assert calculate_request({
        "operation": "laplacian",
        "expression": "x**2 + y**2 + z**2",
        "variables": ["x", "y", "z"],
    }) == 6


def test_multivariable_operations_reject_invalid_or_incompatible_inputs():
    import pytest

    with pytest.raises(CalculatorError, match="valid symbol names"):
        calculate_request({
            "operation": "divergence",
            "expression": "Matrix((x, y))",
            "variables": ["x", "y+1"],
        })
    with pytest.raises(CalculatorError, match="one variable per vector component"):
        calculate_request({
            "operation": "divergence",
            "expression": "Matrix((x, y))",
            "variables": ["x"],
        })
    with pytest.raises(CalculatorError, match="three-dimensional"):
        calculate_request({
            "operation": "curl",
            "expression": "Matrix((y, -x))",
            "variables": ["x", "y"],
        })


def test_total_differential_rejects_generated_symbol_collision():
    import pytest

    requests = [
        {"expression": "x + d_x", "variables": ["x"]},
        {"expression": "x + 1", "variables": ["x", "d_x"]},
    ]
    for request in requests:
        with pytest.raises(CalculatorError, match="must not collide"):
            calculate_request({"operation": "total_differential", **request})
