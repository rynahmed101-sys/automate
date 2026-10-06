"""Isolated executor for applying and testing worker proposals."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from automate.dev.apply import apply_worker_result
from automate.dev.guard import validate_branch_scope
from automate.dev.inventory import InventoryError


class WorkerExecutionError(RuntimeError):
    """Raised when a worker proposal cannot be safely executed."""


def run_approved_tests(
    packet: dict[str, Any],
    *,
    root: Path,
    timeout: int = 600,
) -> dict[str, Any]:
    targets = packet.get("verification", {}).get("test_targets", [])
    if not targets or not all(isinstance(target, str) and target.startswith("tests/") for target in targets):
        raise WorkerExecutionError("worker packet has no valid authoritative test targets")

    command = ["python", "-m", "pytest", "-q", *targets]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorkerExecutionError(f"approved worker tests could not execute: {exc}") from exc

    return {
        "command": command,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
        "authoritative": True,
    }


def execute_worker_proposal(
    packet: dict[str, Any],
    result: dict[str, Any],
    *,
    root: Path,
    branch_name: str,
    run_tests: bool = True,
) -> dict[str, Any]:
    if not branch_name.startswith(packet["constraints"]["branch_prefix"]):
        raise WorkerExecutionError("worker branch violates packet branch prefix")

    changed = apply_worker_result(packet, result, root=root)

    scope_errors = validate_branch_scope(branch_name, changed)
    if scope_errors:
        raise WorkerExecutionError("; ".join(scope_errors))

    test_result = None
    if run_tests:
        test_result = run_approved_tests(packet, root=root)

    if test_result and test_result["status"] != "passed":
        return {
            "status": "tests_failed",
            "changed_files": changed,
            "tests": test_result,
        }

    return {
        "status": "ready_for_commit",
        "changed_files": changed,
        "tests": test_result,
    }


def git_commit(
    *,
    root: Path,
    changed_files: list[str],
    message: str,
) -> str:
    if not changed_files:
        raise WorkerExecutionError("nothing changed; refusing empty worker commit")

    add = subprocess.run(
        ["git", "add", "--", *changed_files],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if add.returncode != 0:
        raise WorkerExecutionError(f"git add failed: {add.stderr.strip()}")

    commit = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if commit.returncode != 0:
        raise WorkerExecutionError(f"git commit failed: {commit.stderr.strip()}")

    rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if rev.returncode != 0:
        raise WorkerExecutionError(f"git rev-parse failed: {rev.stderr.strip()}")
    sha = rev.stdout.strip()
    if len(sha) != 40:
        raise WorkerExecutionError("git did not return a valid commit sha")
    return sha
