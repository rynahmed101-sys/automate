"""
Tests for the public calculator CLI.
"""
import json
from click.testing import CliRunner
from automate.cli import main

def test_cli_capabilities_json():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["symbolic"] is True
    assert data["numerical"] is True
    assert data["linear_algebra"] is True
    assert "providers" not in data

def test_cli_calculate_derivative_json():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "differentiate",
        "--expression", "x**2*y + sin(x*y)", "--variable", "x", "--json"
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["result"] == "2*x*y + y*cos(x*y)"

def test_cli_calculate_integral():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "integrate",
        "--expression", "2*x", "--variable", "x"
    ])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "x**2"

def test_cli_calculate_solve():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "solve",
        "--expression", "x**2 - 4", "--variable", "x", "--json"
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "[-2, 2]"

def test_cli_schema_ir():
    result = CliRunner().invoke(main, ["schema", "--name", "ir"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "$schema" in data or "title" in data or "type" in data

def test_cli_capabilities_publish_calculator_operations():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "differentiate" in data["calculator_operations"]
    assert "gradient" in data["calculator_operations"]
    assert "matrix_eigenvalues" in data["calculator_operations"]

def test_cli_calculate_substitute_and_multivariable():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "substitute",
        "--expression", "x**2 + y", "--value", "x=3", "--json"
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "y + 9"

    result = CliRunner().invoke(main, [
        "calculate", "--operation", "gradient",
        "--expression", "x**2 + x*y + y**2",
        "--variables", "x,y", "--json"
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "Matrix([[2*x + y], [x + 2*y]])"

def test_cli_calculate_matrix_operations():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "matrix_determinant",
        "--expression", "Matrix((1,2),(3,4))", "--json"
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "-2"

    result = CliRunner().invoke(main, [
        "calculate", "--operation", "vector_dot",
        "--expression", "Matrix((1,2,3))",
        "--second-expression", "Matrix((4,5,6))", "--json"
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "32"
