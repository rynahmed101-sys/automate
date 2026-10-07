"""Build and optionally publish an isolated worker capability branch."""

from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from automate.dev.executor import WorkerExecutionError, execute_worker_proposal, git_commit
from automate.dev.prmgr import create_worker_pr


@contextmanager
def isolated_worker_worktree(
    repository_root: Path,
    *,
    base_sha: str,
    branch_name: str,
) -> Iterator[Path]:
    if not len(base_sha) == 40 or any(ch not in "0123456789abcdef" for ch in base_sha):
        raise WorkerExecutionError("invalid base sha for isolated worker worktree")
    if not branch_name.startswith("feat/"):
        raise WorkerExecutionError("worker branch must start with feat/")

    verify = subprocess.run(
        ["git", "cat-file", "-e", base_sha + "^{commit}"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        raise WorkerExecutionError(
            f"base sha is not available in local repository: {base_sha}"
        )

    tempdir = Path(tempfile.mkdtemp(prefix="automate-worker-"))
    added = subprocess.run(
        ["git", "worktree", "add", "--detach", str(tempdir), base_sha],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if added.returncode != 0:
        tempdir.rmdir()
        raise WorkerExecutionError(f"git worktree add failed: {added.stderr.strip()}")

    switched = subprocess.run(
        ["git", "switch", "-c", branch_name],
        cwd=tempdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if switched.returncode != 0:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tempdir)],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        raise WorkerExecutionError(f"git switch failed: {switched.stderr.strip()}")

    try:
        yield tempdir
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tempdir)],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )


def worker_branch_name(capability_id: str) -> str:
    if not capability_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_.-" for ch in capability_id):
        raise WorkerExecutionError("capability id is not safe for a worker branch")
    return "feat/" + capability_id


def build_worker_commit(
    packet: dict,
    result: dict,
    *,
    repository_root: Path,
    commit_message: str | None = None,
    enforce_inventory_scope: bool = True,
) -> dict:
    base_sha = packet.get("repository", {}).get("base_sha_claim")
    if not isinstance(base_sha, str):
        raise WorkerExecutionError("worker packet has no exact base sha")
    capability_id = packet.get("capability", {}).get("id")
    if not isinstance(capability_id, str):
        raise WorkerExecutionError("worker packet has no capability id")

    branch_name = worker_branch_name(capability_id)
    message = commit_message or (
        "feat: implement " + str(packet["capability"]["name"])
    )

    with isolated_worker_worktree(
        repository_root,
        base_sha=base_sha,
        branch_name=branch_name,
    ) as worktree:
        execution = execute_worker_proposal(
            packet,
            result,
            root=worktree,
            branch_name=branch_name,
            run_tests=True,
            enforce_inventory_scope=enforce_inventory_scope,
        )
        if execution["status"] != "ready_for_commit":
            return {
                "status": execution["status"],
                "branch": branch_name,
                "changed_files": execution["changed_files"],
                "tests": execution["tests"],
            }

        commit_sha = git_commit(
            root=worktree,
            changed_files=execution["changed_files"],
            message=message,
        )

    return {
        "status": "committed",
        "branch": branch_name,
        "commit_sha": commit_sha,
        "changed_files": execution["changed_files"],
        "tests": execution["tests"],
        "request_id": packet.get("request_id"),
        "capability_id": capability_id,
        "base_sha": base_sha,
    }


def push_worker_branch(
    repository_root: Path,
    *,
    branch_name: str,
) -> str:
    if not branch_name.startswith("feat/"):
        raise WorkerExecutionError("refusing to push non-worker branch")

    result = subprocess.run(
        ["git", "push", "--set-upstream", "origin", branch_name],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise WorkerExecutionError(f"git push failed: {result.stderr.strip()}")
    return branch_name



def publish_worker_commit(
    repository: str,
    repository_root: Path,
    *,
    packet: dict[str, Any],
    commit: dict[str, Any],
) -> dict[str, Any]:
    """Push a validated worker branch and open its promotion-ready PR."""
    if commit.get("status") != "committed":
        raise WorkerExecutionError("only committed worker results can be published")
    branch_name = commit.get("branch")
    if not isinstance(branch_name, str):
        raise WorkerExecutionError("committed worker result has no branch")
    request_id = packet.get("request_id")
    capability_id = packet.get("capability", {}).get("id")
    base_sha = packet.get("repository", {}).get("base_sha_claim")
    if not all(isinstance(value, str) for value in (request_id, capability_id, base_sha)):
        raise WorkerExecutionError("worker packet is missing publication identity")

    push_worker_branch(repository_root, branch_name=branch_name)
    pr = create_worker_pr(
        repository,
        branch=branch_name,
        capability_id=capability_id,
        title="feat: implement " + str(packet["capability"]["name"]),
        base_sha=base_sha,
        request_id=request_id,
        test_result=commit.get("tests") or {},
    )
    return {
        **commit,
        "status": "submitted",
        "pr_number": pr.get("pr_number"),
        "pr_url": pr.get("url"),
        "pr": pr,
    }
