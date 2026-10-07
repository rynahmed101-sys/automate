"""Tests for controlled GitHub PR handoff."""

from unittest.mock import patch

from automate.dev.prmgr import create_worker_pr
from automate.dev.executor import WorkerExecutionError


def test_create_worker_pr_rejects_non_worker_branch():
    with patch.dict("os.environ", {"GH_TOKEN": "secret"}):
        try:
            create_worker_pr(
                "owner/repo",
                branch="integrate/bad",
                capability_id="stage1b.improper_integrals",
                title="x",
                base_sha="0" * 40,
                test_result={"status": "passed", "command": ["python", "-m", "pytest"]},
                worker_request_id="wrk_" + "a" * 32,
            )
        except WorkerExecutionError as exc:
            assert "non-worker branch" in str(exc)
        else:
            raise AssertionError("unsafe branch was accepted")


def test_create_worker_pr_emits_deterministic_handoff_metadata_and_ready_state():
    with patch.dict("os.environ", {"GH_TOKEN": "secret"}), patch(
        "automate.dev.prmgr.subprocess.run"
    ) as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "https://github.com/owner/repo/pull/1\\n"
        run.return_value.stderr = ""
        result = create_worker_pr(
            "owner/repo",
            branch="feat/stage1b.improper_integrals",
            capability_id="stage1b.improper_integrals",
            title="feat: implement improper integrals",
            base_sha="0" * 40,
            test_result={"status": "passed", "command": ["python", "-m", "pytest", "-q", "tests/test_improper_integrals.py"]},
        )
    assert result["draft"] is False
    assert result["worker_request_id"] == "wrk_" + "a" * 32
    command = run.call_args.args[0]
    assert "--draft" not in command
    assert "--base" in command
    assert "main" in command
