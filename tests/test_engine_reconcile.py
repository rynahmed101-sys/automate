from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from automate.dev.engine_reconcile import reconcile_engine


def test_reconcile_aligned_when_engine_contains_main(tmp_path: Path):
    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_reconcile._run", fake):
        result = reconcile_engine(tmp_path, "rynahmed101-sys/automate")

    assert result["state"] == "ALIGNED"
    assert result["action"] == "none"


def test_reconcile_conflict_fails_closed(tmp_path: Path):
    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 1, stdout="", stderr="")
        if args[:2] == ["gh", "pr"] and args[2] == "list":
            return CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:2] == ["git", "merge"] and "--no-ff" in args:
            return CompletedProcess(args, 1, stdout="", stderr="conflict")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_reconcile._run", fake):
        result = reconcile_engine(tmp_path, "rynahmed101-sys/automate")

    assert result["state"] == "CONFLICT"
    assert result["action"] == "manual_reconciliation_required"


def test_reconcile_never_force_pushes(tmp_path: Path):
    seen = []

    def fake(root, args, check=False):
        seen.append(args)
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return CompletedProcess(args, 1, stdout="", stderr="")
        if args[:2] == ["gh", "pr"] and args[2] == "list":
            return CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:2] == ["git", "merge"] and "--no-ff" in args:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, stdout="c" * 40 + "\n", stderr="")
        if args[:2] == ["git", "push"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["gh", "pr"]:
            return CompletedProcess(args, 0, stdout="https://github.com/example/pr/1\n", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_reconcile._run", fake):
        reconcile_engine(tmp_path, "rynahmed101-sys/automate")

    assert not any("--force" in arg or "--force-with-lease" in arg for args in seen for arg in args)


def test_reconcile_rejects_malformed_main_sha(tmp_path):
    def fake(root, args, check=False):
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/main"]:
            return CompletedProcess(args, 0, stdout="not-a-sha\n", stderr="")
        if args[:3] == ["git", "rev-parse", "refs/remotes/origin/engine"]:
            return CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("automate.dev.engine_reconcile._run", fake):
        try:
            reconcile_engine(tmp_path, "rynahmed101-sys/automate")
        except Exception as exc:
            assert "malformed" in str(exc)
        else:
            raise AssertionError("malformed main SHA must be rejected")
