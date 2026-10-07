"""Evidence-gated promotion state machine for canonical capability PRs.

The controller may recommend or execute promotion of an ordinary capability PR.
It never promotes control-plane, reconciliation, constitutional, or research
proposal changes. Post-merge verification is a separate state and exact-main
evidence is required before certification bookkeeping can proceed.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Mapping

from automate.dev.inventory import load_inventory


class PromotionError(RuntimeError):
    """Raised when the promotion controller cannot safely inspect or execute."""


WORKFLOW_CI = "ci.yml"
WORKFLOW_SECURITY = "security.yml"


def _github_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise PromotionError("GH_TOKEN or GITHUB_TOKEN is required for promotion control")
    return env


def _gh_json(repository: str, *args: str) -> Any:
    endpoint = "repos/" + repository
    endpoint += "".join(args)
    command = ["gh", "api", endpoint]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=_github_env(),
    )
    if result.returncode != 0:
        raise PromotionError(result.stderr.strip() or "GitHub query failed")
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        raise PromotionError("GitHub query returned invalid JSON") from exc


def _workflow_runs(repository: str, workflow_file: str, commit_sha: str) -> list[dict[str, Any]]:
    payload = _gh_json(
        repository,
        f"/actions/workflows/{workflow_file}/runs?head_sha={commit_sha}&per_page=20",
    )
    runs = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
    return [dict(run) for run in runs if isinstance(run, dict)]


def _latest_completed_success(repository: str, workflow_file: str, commit_sha: str) -> dict[str, Any] | None:
    runs = [
        run
        for run in _workflow_runs(repository, workflow_file, commit_sha)
        if run.get("status") == "completed"
    ]
    if not runs:
        return None
    runs.sort(key=lambda run: str(run.get("updated_at") or run.get("created_at") or ""), reverse=True)
    run = runs[0]
    return run if run.get("conclusion") == "success" else None


def _pr(repository: str, pr_number: int) -> dict[str, Any]:
    payload = _gh_json(
        repository,
        f"/pulls/{pr_number}",
    )
    if not isinstance(payload, dict):
        raise PromotionError("GitHub pull request query returned a non-object payload")
    return payload


def _capability_owner(data: Mapping[str, Any], pr_number: int) -> str | None:
    owners: list[str] = []
    for item in data.get("capabilities", []):
        if item.get("implementation_state") not in {
            "active_development",
            "delegated",
            "awaiting_reconciliation",
            "reconciled",
        }:
            continue
        for ref in item.get("references", []):
            if (
                ref.get("type") == "pr"
                and ref.get("number") == pr_number
                and str(ref.get("state", "")).startswith("open")
                and ref.get("role") != "integration_batch"
            ):
                owners.append(str(item["id"]))
    if len(owners) > 1:
        raise PromotionError(
            f"PR #{pr_number} has multiple canonical capability owners: {', '.join(sorted(owners))}"
        )
    return owners[0] if owners else None


def evaluate_promotion(
    pr: Mapping[str, Any],
    *,
    capability_id: str | None,
    current_main_sha: str,
    ci_run: Mapping[str, Any] | None,
    security_run: Mapping[str, Any] | None,
    require_review: bool = False,
) -> dict[str, Any]:
    """Evaluate only the pre-merge gates for an ordinary capability PR."""
    reasons: list[str] = []
    gates: dict[str, bool] = {}

    gates["capability_owned"] = bool(capability_id)
    if not gates["capability_owned"]:
        reasons.append("PR is not owned by an active canonical capability.")

    gates["open"] = str(pr.get("state", "")).lower() == "open"
    if not gates["open"]:
        reasons.append("PR is not open.")

    gates["not_draft"] = not bool(pr.get("draft"))
    if not gates["not_draft"]:
        reasons.append("PR is still a draft.")

    gates["targets_main"] = pr.get("base", {}).get("ref") == "main"
    if not gates["targets_main"]:
        reasons.append("Capability promotion requires base branch main.")

    gates["base_is_current"] = pr.get("base", {}).get("sha") == current_main_sha
    if not gates["base_is_current"]:
        reasons.append("PR base SHA is stale; reconciliation is required before promotion.")

    mergeable = pr.get("mergeable")
    gates["mergeable"] = mergeable is True
    if mergeable is not True:
        reasons.append("GitHub does not currently report the PR as mergeable.")

    gates["development_ci_verified"] = bool(
        ci_run and ci_run.get("status") == "completed" and ci_run.get("conclusion") == "success"
    )
    if not gates["development_ci_verified"]:
        reasons.append("Development CI has not completed successfully on the exact PR head.")

    gates["security_audit_verified"] = bool(
        security_run and security_run.get("status") == "completed" and security_run.get("conclusion") == "success"
    )
    if not gates["security_audit_verified"]:
        reasons.append("Security Audit has not completed successfully on the exact PR head.")

    review_decision = str(pr.get("review_decision") or "").upper()
    if require_review:
        gates["review_gate"] = review_decision == "APPROVED"
        if not gates["review_gate"]:
            reasons.append(f"Required review approval is absent (current decision: {review_decision or 'NONE'}).")
    else:
        gates["review_gate"] = review_decision not in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}
        if not gates["review_gate"]:
            reasons.append(f"Review state blocks promotion: {review_decision}.")

    ready = all(gates.values())
    return {
        "schema_version": "automate.promotion_gate.v1",
        "state": "READY_TO_MERGE" if ready else "BLOCKED",
        "capability_id": capability_id,
        "pr_number": pr.get("number"),
        "head_sha": pr.get("head", {}).get("sha"),
        "current_main_sha": current_main_sha,
        "gates": gates,
        "reasons": reasons,
        "post_merge_action": (
            "MERGE_THEN_WAIT_FOR_EXACT_HEAD_AND_SECURITY_ON_NEW_MAIN"
            if ready
            else None
        ),
    }


def inspect_promotion(
    repository: str,
    pr_number: int,
    *,
    current_main_sha: str,
    require_review: bool = False,
) -> dict[str, Any]:
    data = load_inventory()
    pr = _pr(repository, pr_number)
    capability_id = _capability_owner(data, pr_number)
    head_sha = str(pr.get("head", {}).get("sha") or "")
    ci = _latest_completed_success(repository, WORKFLOW_CI, head_sha) if head_sha else None
    security = _latest_completed_success(repository, WORKFLOW_SECURITY, head_sha) if head_sha else None
    result = evaluate_promotion(
        pr,
        capability_id=capability_id,
        current_main_sha=current_main_sha,
        ci_run=ci,
        security_run=security,
        require_review=require_review,
    )
    result["observed"] = {
        "ci_run_id": ci.get("id") if ci else None,
        "security_run_id": security.get("id") if security else None,
    }
    return result


def execute_promotion(
    repository: str,
    pr_number: int,
    *,
    current_main_sha: str,
    execute: bool = False,
    require_review: bool = False,
) -> dict[str, Any]:
    """Merge only when every pre-merge gate passes and execution is explicitly enabled."""
    result = inspect_promotion(
        repository,
        pr_number,
        current_main_sha=current_main_sha,
        require_review=require_review,
    )
    if result["state"] != "READY_TO_MERGE":
        return {**result, "execution": "not_ready"}

    if not execute:
        return {**result, "execution": "dry_run_ready"}

    if os.getenv("AUTOMATE_AUTO_PROMOTE", "").strip().lower() not in {"1", "true", "yes"}:
        return {
            **result,
            "execution": "blocked_by_governance",
            "reasons": [*result["reasons"], "AUTOMATE_AUTO_PROMOTE is not enabled."],
        }

    expected_head_sha = result.get("head_sha")
    command = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--repo",
        repository,
        "--merge",
        "--delete-branch=false",
        "--match-head-commit",
        str(expected_head_sha),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=_github_env(),
    )
    if completed.returncode != 0:
        raise PromotionError(completed.stderr.strip() or "GitHub refused promotion merge")

    return {
        **result,
        "execution": "merged_pending_exact_head_verification",
        "merge_output": completed.stdout.strip(),
        "expected_head_sha": expected_head_sha,
    }


def evaluate_post_merge(
    *,
    capability_id: str,
    merged_main_sha: str,
    exact_head_ci_run: Mapping[str, Any] | None,
    exact_head_security_run: Mapping[str, Any] | None,
) -> dict[str, Any]:
    gates = {
        "merged_main": bool(merged_main_sha and len(merged_main_sha) == 40),
        "exact_head_ci_verified": bool(
            exact_head_ci_run
            and exact_head_ci_run.get("status") == "completed"
            and exact_head_ci_run.get("conclusion") == "success"
            and exact_head_ci_run.get("head_sha") == merged_main_sha
        ),
        "security_audit_verified": bool(
            exact_head_security_run
            and exact_head_security_run.get("status") == "completed"
            and exact_head_security_run.get("conclusion") == "success"
            and exact_head_security_run.get("head_sha") == merged_main_sha
        ),
    }
    ready = all(gates.values())
    return {
        "schema_version": "automate.promotion_post_merge.v1",
        "state": "BOOKKEEPING_READY" if ready else "VERIFYING_EXACT_MAIN",
        "capability_id": capability_id,
        "merged_main_sha": merged_main_sha,
        "gates": gates,
        "reasons": [] if ready else [
            name for name, passed in gates.items() if not passed
        ],
        "canonical_ledger_mutated": False,
    }


def inspect_post_merge(
    repository: str,
    *,
    capability_id: str,
    merged_main_sha: str,
) -> dict[str, Any]:
    ci = _latest_completed_success(repository, WORKFLOW_CI, merged_main_sha)
    security = _latest_completed_success(repository, WORKFLOW_SECURITY, merged_main_sha)
    return evaluate_post_merge(
        capability_id=capability_id,
        merged_main_sha=merged_main_sha,
        exact_head_ci_run=ci,
        exact_head_security_run=security,
    )
