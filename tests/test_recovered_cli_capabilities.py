import json
import math

from click.testing import CliRunner

from automate.cli import main


def test_cli_unit_conversion_json():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "unit_convert", "--expression", "1",
        "--source-unit", "km", "--target-unit", "m", "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["operation"] == "unit_convert"
    assert payload["result_data"]["type"] == "quantity"
    assert math.isclose(payload["result_data"]["magnitude"]["value"], 1000.0)


def test_cli_distribution_json_parameters():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "distribution", "--expression", "0",
        "--distribution-name", "normal", "--distribution-function", "pdf",
        "--distribution-parameters", '{"loc": 0, "scale": 1}', "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert math.isclose(float(payload["result"]), 1 / math.sqrt(2 * math.pi))


def test_cli_capability_manifest_lists_recovered_operations():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    operations = set(payload["calculator_operations"])
    assert {"unit_convert", "descriptive_statistics", "distribution", "pde_solve"} <= operations


def test_cli_calculate_exposes_definite_integral_bounds():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "integrate_definite", "--expression", "x**2",
        "--variable", "x", "--lower", "0", "--upper", "3", "--json",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "9"


def test_cli_calculate_exposes_equation_systems():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "solve_system", "--expression", "x+y+z-6",
        "--variables", "x,y,z", "--equations", '["x-1", "y-2", "z-3"]', "--json",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "{x: 1, y: 2, z: 3}"


def test_cli_calculate_exposes_transform_arguments():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "transform", "--expression", "exp(2*t)",
        "--variable", "t", "--transform-type", "laplace",
        "--transform-variable", "s", "--json",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "1/(s - 2)"


def test_cli_calculate_exposes_vector_calculus_arguments():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "divergence",
        "--expression", "Matrix((x, y, z))", "--variables", "x,y,z", "--json",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["result"] == "3"


def test_cli_calculate_json_errors_return_nonzero():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "integrate_definite", "--expression", "x**2",
        "--variable", "x", "--lower", "0", "--json",
    ])
    assert result.exit_code == 1, result.output
    assert "both lower and upper bounds" in json.loads(result.output)["error"]


def test_cli_calculate_rejects_malformed_json_arguments():
    result = CliRunner().invoke(main, [
        "calculate", "--operation", "solve_system", "--expression", "x+y",
        "--variables", "x,y", "--equations", "not-json", "--json",
    ])
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error"].startswith("JSONDecodeError:")
