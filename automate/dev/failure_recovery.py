"""Fail-closed recovery evidence for worker verification failures.

This module is deliberately narrower than the old self-correction packet. It
answers one question: what is the exact verification state of one worker PR
head, and what bounded recovery action is justified? It does not certify
science or mutate canonical inventory/ledger state.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


WORKFLOWS = ("ci.yml", "security.yml")


class RecoveryError(RuntimeError):
    """Raised when recovery evidence cannot be established safely."""


def _env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise RecoveryError("GH_TOKEN or GITHUB_TOKEN is required for recovery inspection")
    return env


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False, env=_env())


def workflow_runs(
    repository: str,
    workflow_file: str,
    head_sha: str,
) -> list[dict[str, Any]]:
    if len(head_sha) != 40:
        raise RecoveryError("recovery requires a full 40-character head SHA")
    result = _run([
        "gh", "api",
        f"repos/{repository}/actions/workflows/{workflow_file}/runs?head_sha={head_sha}&per_page=50",
    ])
    if result.returncode != 0:
        raise RecoveryError(result.stderr.strip() or "GitHub workflow query failed")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RecoveryError("GitHub workflow query returned invalid JSON") from exc
    rows = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
    return [dict(row) for row in rows if isinstance(row, dict) and row.get("head_sha") == head_sha]


def exact_head_recovery_state(
    repository: str,
    head_sha: str,
) -> dict[str, Any]:
    """Classify exact-head CI/security evidence without collapsing failures."""
    runs_by_workflow = {
        workflow: workflow_runs(repository, workflow, head_sha)
        for workflow in WORKFLOWS
    }
    failures: list[dict[str, Any]] = []
    pending: list[str] = []
    successful: list[str] = []

    for workflow, rows in runs_by_workflow.items():
        completed = [
            row for row in rows
            if row.get("status") == "completed"
        ]
        active = [
            row for row in rows
            if row.get("status") in {"queued", "in_progress", "waiting", "requested"}
        ]
        if active:
            pending.append(workflow)

        if not completed:
            if not active:
                pending.append(workflow)
            continue

        latest = max(
            completed,
            key=lambda row: (
                int(row.get("run_attempt") or 0),
                str(row.get("updated_at") or row.get("created_at") or ""),
            ),
        )
        if latest.get("conclusion") == "success":
            successful.append(workflow)
        else:
            failures.append({
                "workflow": workflow,
                "run_id": latest.get("id"),
                "attempt": int(latest.get("run_attempt") or 1),
                "conclusion": latest.get("conclusion"),
                "url": latest.get("html_url"),
            })

    if pending:
        return {
            "state": "pending",
            "pending": sorted(set(pending)),
            "failures": failures,
            "successful": sorted(successful),
            "runs": runs_by_workflow,
        }
    if failures:
        retryable = [
            failure for failure in failures
            if int(failure.get("attempt") or 1) < 2
            and isinstance(failure.get("run_id"), int)
        ]
        return {
            "state": "retryable_failure" if retryable else "repeated_failure",
            "pending": [],
            "failures": failures,
            "retryable": retryable,
            "successful": sorted(successful),
            "runs": runs_by_workflow,
        }
    return {
        "state": "success",
        "pending": [],
        "failures": [],
        "retryable": [],
        "successful": sorted(successful),
        "runs": runs_by_workflow,
    }


def rerun_failed_workflows(
    repository: str,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Request retries only for failed workflow runs identified by exact SHA."""
    requested: list[int] = []
    errors: list[str] = []
    for failure in failures:
        run_id = failure.get("run_id")
        if not isinstance(run_id, int):
            continue
        result = _run([
            "gh", "run", "rerun", str(run_id),
            "--repo", repository,
            "--failed",
        ])
        if result.returncode == 0:
            requested.append(run_id)
        else:
            errors.append(
                result.stderr.strip()
                or result.stdout.strip()
                or f"rerun failed for workflow run {run_id}"
            )
    return {"requested": requested, "errors": errors}


def quarantine_worker_pr(
    repository: str,
    pr_number: int,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Close a repeatedly failing worker PR with machine-readable evidence."""
    body = (
        "AUTONOMOUS RECOVERY: this worker proposal failed exact-head verification "
        "repeatedly and has been quarantined. It is not certified or promoted.\n\n"
        "Failure evidence:\n"
        + json.dumps(failures, sort_keys=True)
    )
    result = _run([
        "gh", "pr", "close", str(pr_number),
        "--repo", repository,
        "--comment", body,
    ])
    if result.returncode != 0:
        return {
            "state": "quarantine_failed",
            "pr_number": pr_number,
            "error": result.stderr.strip() or result.stdout.strip(),
        }
    return {
        "state": "quarantined",
        "pr_number": pr_number,
        "failures": failures,
    }


def diagnose_worker_failure(
    repository: str,
    pr_number: int,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a bounded diagnosis record from failed runs and PR diff metadata."""
    diff = _run(["gh", "pr", "diff", str(pr_number), "--repo", repository])
    changed_paths: list[str] = []
    if diff.returncode == 0:
        for line in diff.stdout.splitlines():
            if line.startswith("diff --git a/"):
                parts = line.split()
                if len(parts) >= 4:
                    changed_paths.append(parts[3][2:])

    classes: set[str] = set()
    notes: list[str] = [
        "Do not reproduce the failed proposal unchanged.",
        "Inspect changed paths and exact failed workflow evidence before repair.",
    ]
    for failure in failures[:4]:
        run_id = failure.get("run_id")
        if not isinstance(run_id, int):
            continue
        result = _run([
            "gh", "run", "view", str(run_id),
            "--repo", repository,
            "--log-failed",
        ])
        log = result.stdout[-5000:] if result.returncode == 0 else ""
        lowered = log.lower()
        if "syntaxerror" in lowered or "indentationerror" in lowered:
            classes.add("syntax")
        elif "modulenotfounderror" in lowered or "importerror" in lowered:
            classes.add("import")
        elif "typeerror" in lowered:
            classes.add("type")
        elif "assertionerror" in lowered or "failed" in lowered:
            classes.add("test_or_assertion")
        elif "timeout" in lowered or "timed out" in lowered:
            classes.add("timeout")
        elif log:
            classes.add("unknown")
        if log:
            notes.append(
                f"workflow={failure.get('workflow')} "
                f"run_id={run_id} classes={','.join(sorted(classes))}\n{log}"
            )

    return {
        "state": "diagnosed" if classes else "evidence_limited",
        "changed_paths": changed_paths[:50],
        "failure_classes": sorted(classes or {"unknown"}),
        "notes": notes,
    }
