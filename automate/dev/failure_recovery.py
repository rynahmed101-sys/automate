"""Fail-closed recovery for autonomous worker PR verification failures."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


def _env() -> dict[str, str]:
    return os.environ.copy()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False, env=_env())


def _workflow_runs(repository: str, workflow: str, head_sha: str) -> list[dict[str, Any]]:
    result = _run([
        "gh", "run", "list", "--repo", repository, "--workflow", workflow,
        "--commit", head_sha, "--limit", "20",
        "--json", "databaseId,conclusion,attempt,status,headSha,name,url",
    ])
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [row for row in payload if isinstance(row, dict) and row.get("headSha") == head_sha]


def exact_head_recovery_state(repository: str, head_sha: str) -> dict[str, Any]:
    workflows = ("Automate CI", "Security Audit")
    runs: dict[str, list[dict[str, Any]]] = {
        name: _workflow_runs(repository, name, head_sha) for name in workflows
    }
    failures: list[dict[str, Any]] = []
    pending = False
    missing = []
    for name, rows in runs.items():
        completed = [r for r in rows if r.get("status") == "completed"]
        if not completed:
            pending = True
            missing.append(name)
            continue
        latest = max(completed, key=lambda r: int(r.get("attempt") or 0))
        if latest.get("conclusion") != "success":
            failures.append({
                "workflow": name,
                "run_id": latest.get("databaseId"),
                "attempt": int(latest.get("attempt") or 0),
                "conclusion": latest.get("conclusion"),
                "url": latest.get("url"),
            })
        elif any(r.get("status") in {"queued", "in_progress", "waiting", "requested"} for r in rows):
            pending = True

    if pending:
        return {"state": "pending", "failures": failures, "missing": missing, "runs": runs}
    if failures:
        retryable = [f for f in failures if int(f["attempt"]) < 2 and isinstance(f.get("run_id"), int)]
        if retryable:
            return {"state": "retryable_failure", "failures": failures, "retryable": retryable, "runs": runs}
        return {"state": "repeated_failure", "failures": failures, "runs": runs}
    return {"state": "success", "failures": [], "runs": runs}


def rerun_failed_workflows(repository: str, failures: list[dict[str, Any]]) -> dict[str, Any]:
    requested: list[int] = []
    errors: list[str] = []
    for failure in failures:
        run_id = failure.get("run_id")
        if not isinstance(run_id, int):
            continue
        result = _run(["gh", "run", "rerun", str(run_id), "--repo", repository, "--failed"])
        if result.returncode == 0:
            requested.append(run_id)
        else:
            errors.append(result.stderr.strip() or result.stdout.strip() or f"rerun failed for {run_id}")
    return {"requested": requested, "errors": errors}


def quarantine_worker_pr(repository: str, pr_number: int, failures: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = json.dumps(failures, sort_keys=True)
    body = (
        "AUTONOMOUS RECOVERY: this worker proposal failed exact-head verification twice. "
        "The proposal is quarantined and will not be promoted. A fresh repair attempt must "
        "be generated from authoritative main with this failure evidence.

"
        "Failure evidence:
" + evidence
    )
    result = _run([
        "gh", "pr", "close", str(pr_number), "--repo", repository,
        "--comment", body,
    ])
    if result.returncode != 0:
        return {"status": "quarantine_failed", "error": result.stderr.strip() or result.stdout.strip()}
    return {"status": "quarantined", "pr_number": pr_number, "failures": failures}


def failure_notes(failures: list[dict[str, Any]]) -> list[str]:
    notes = [
        "AUTONOMOUS_RECOVERY: prior worker proposal failed exact-head verification.",
        "AUTONOMOUS_RECOVERY: previous proposal is quarantined; do not reproduce its unchanged implementation.",
    ]
    for failure in failures:
        notes.append(
            "AUTONOMOUS_FAILURE_EVIDENCE: workflow="
            + str(failure.get("workflow"))
            + " attempt="
            + str(failure.get("attempt"))
            + " conclusion="
            + str(failure.get("conclusion"))
            + " run_id="
            + str(failure.get("run_id"))
        )
    return notes
