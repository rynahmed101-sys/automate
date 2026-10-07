from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from automate.dev.engine_pin import ensure_engine_pin


def _pin(tmp_path: Path):
    path = tmp_path / "docs"
    path.mkdir()
    (path / "CONTROL_PLANE_ENGINE_PIN.json").write_text(
        '{"schema_version":"automate.control_plane_pin.v1","enabled":false,"engine_sha":null,"auto_promote":false,"notes":"x"}\n',
        encoding="utf-8",
    )


def test_engine_pin_waits_for_alignment(tmp_path: Path):
    _pin(tmp_path)

    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 1, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_pin._run", fake):
        result = ensure_engine_pin(tmp_path, "rynahmed101-sys/automate")

    assert result["state"] == "ENGINE_NOT_ALIGNED"


def test_engine_pin_never_updates_without_explicit_auto_update(tmp_path: Path):
    _pin(tmp_path)

    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["gh", "api"]:
            return CompletedProcess(args, 0, stdout='{"workflow_runs":[{"name":"Automate Engine CI","status":"completed","conclusion":"success"},{"name":"Security Audit","status":"completed","conclusion":"success"}]}', stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_pin._run", fake):
        result = ensure_engine_pin(tmp_path, "rynahmed101-sys/automate", auto_update=False)

    assert result["state"] == "PIN_UPDATE_REQUIRED"
    assert json_path(tmp_path).get("engine_sha") is None


def json_path(tmp_path: Path):
    import json
    return json.loads((tmp_path / "docs/CONTROL_PLANE_ENGINE_PIN.json").read_text(encoding="utf-8"))


def test_engine_pin_reports_missing_release_evidence(tmp_path: Path):
    _pin(tmp_path)

    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["gh", "api"]:
            return CompletedProcess(args, 0, stdout='{"workflow_runs":[]}', stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_pin._run", fake):
        result = ensure_engine_pin(tmp_path, "rynahmed101-sys/automate")

    assert result["state"] == "ENGINE_UNVERIFIED"
