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
