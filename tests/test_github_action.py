import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


def _calculator_step():
    action_path = Path(__file__).parents[1] / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))

    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["request"]["required"] is True
    assert set(action["outputs"]) == {"response", "result", "result_data"}

    return next(
        step for step in action["runs"]["steps"] if step.get("id") == "calculate"
    )


def _run_calculator_step(request, output_file):
    step = _calculator_step()
    env = os.environ.copy()
    env.update({
        "AUTOMATE_REQUEST_JSON": json.dumps(request),
        "GITHUB_OUTPUT": str(output_file),
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{env['PATH']}",
    })
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step["run"]],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


def _read_outputs(output_file):
    lines = output_file.read_text(encoding="utf-8").splitlines()
    outputs = {}
    index = 0
    while index < len(lines):
        name, delimiter = lines[index].split("<<", maxsplit=1)
        index += 1
        value = []
        while lines[index] != delimiter:
            value.append(lines[index])
            index += 1
        outputs[name] = "\n".join(value)
        index += 1
    return outputs


def test_github_action_exposes_public_calculator_request_and_outputs():
    calculate_step = _calculator_step()
    assert calculate_step["env"]["AUTOMATE_REQUEST_JSON"] == "${{ inputs.request }}"
    assert "automate request" in calculate_step["run"]


def test_github_action_runs_calculation_and_exports_json_outputs(tmp_path):
    output_file = tmp_path / "github-output"
    completed = _run_calculator_step({
        "operation": "differentiate",
        "expression": "x**2*y",
        "variable": "x",
    }, output_file)

    assert completed.returncode == 0, completed.stderr
    outputs = _read_outputs(output_file)
    response = json.loads(outputs["response"])
    assert response["ok"] is True
    assert response["result"] == "2*x*y"
    assert outputs["result"] == "2*x*y"
    assert json.loads(outputs["result_data"]) == response["result_data"]


def test_github_action_fails_without_writing_outputs_for_invalid_request(tmp_path):
    output_file = tmp_path / "github-output"
    completed = _run_calculator_step({
        "operation": "not_an_operation",
        "expression": "x",
    }, output_file)

    assert completed.returncode != 0
    assert not output_file.exists()
