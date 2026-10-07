import json
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
        if args[:2] == ["gh", "api"]:
            return CompletedProcess(args, 0, stdout='{"workflow_runs":[{"name":"Automate Engine CI","status":"completed","conclusion":"success"},{"name":"Security Audit","status":"completed","conclusion":"success"}]}', stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_pin._run", fake):
        result = ensure_engine_pin(tmp_path, "rynahmed101-sys/automate", auto_update=False)

    assert result["state"] == "PIN_UPDATE_REQUIRED"  # evidence mock is served by gh api
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


def test_pin_auto_merge_requires_workflow_level_main_pr_checks():
    from automate.dev import engine_pin

    runs = [
        {"name": "Automate CI", "status": "completed", "conclusion": "success"},
        {"name": "Security Audit", "status": "completed", "conclusion": "success"},
    ]

    def fake(root, args, check=False):
        return CompletedProcess(args, 0, stdout=json.dumps({"workflow_runs": runs}), stderr="")

    with patch.object(engine_pin, "_run", fake):
        assert engine_pin._exact_main_pr_checks_verified(Path("."), "owner/repo", "a" * 40) is True


def test_pin_auto_merge_fails_closed_when_main_pr_workflow_is_missing():
    from automate.dev import engine_pin

    runs = [
        {"name": "Security Audit", "status": "completed", "conclusion": "success"},
    ]

    def fake(root, args, check=False):
        return CompletedProcess(args, 0, stdout=json.dumps({"workflow_runs": runs}), stderr="")

    with patch.object(engine_pin, "_run", fake):
        assert engine_pin._exact_main_pr_checks_verified(Path("."), "owner/repo", "a" * 40) is False


def test_pin_creation_auto_merge_uses_created_commit_sha(tmp_path: Path):
    _pin(tmp_path)
    main_sha = "a" * 40
    engine_sha = "b" * 40
    created_sha = "c" * 40

    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout=main_sha + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout=engine_sha + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["gh", "api"] and f"head_sha={engine_sha}" in args[2]:
            return CompletedProcess(
                args, 0,
                stdout=json.dumps({"workflow_runs": [
                    {"name": "Automate Engine CI", "status": "completed", "conclusion": "success"},
                    {"name": "Security Audit", "status": "completed", "conclusion": "success"},
                ]}),
                stderr="",
            )
        if args[:3] == ["gh", "pr", "list"] and "--head" in args and "--json" in args:
            if args[args.index("--json") + 1] == "number,url,headRefName,headRefOid":
                return CompletedProcess(args, 0, stdout="[]", stderr="")
            if args[args.index("--json") + 1] == "number":
                return CompletedProcess(args, 0, stdout=json.dumps([{"number": 177}]), stderr="")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, stdout=created_sha + "\n", stderr="")
        if args[:2] == ["gh", "api"] and f"head_sha={created_sha}" in args[2]:
            return CompletedProcess(
                args, 0,
                stdout=json.dumps({"workflow_runs": [
                    {"name": "Automate CI", "status": "completed", "conclusion": "success"},
                    {"name": "Security Audit", "status": "completed", "conclusion": "success"},
                ]}),
                stderr="",
            )
        return CompletedProcess(args, 0, stdout="https://github.com/rynahmed101-sys/automate/pull/177\n", stderr="")

    with patch("automate.dev.engine_pin._run", fake):
        result = ensure_engine_pin(
            tmp_path,
            "rynahmed101-sys/automate",
            auto_update=True,
            auto_merge=True,
        )

    assert result["state"] == "PIN_PR_AUTO_MERGE_REQUESTED"
