"""Evidence-gated promotion state machine for canonical capability PRs.

The controller may recommend or execute promotion of an ordinary capability PR.
It never promotes control-plane, reconciliation, constitutional, or research
proposal changes. Post-merge verification is a separate state and exact-main
evidence is required before certification bookkeeping can proceed.
"""

from __future__ import annotations

import json
import os
import re
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
        if item.get("implementation_state") in {"merged_main", "superseded", "abandoned"}:
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

    head_sha = pr.get("head", {}).get("sha")
    gates["head_sha_valid"] = isinstance(head_sha, str) and len(head_sha) == 40
    if not gates["head_sha_valid"]:
        reasons.append("PR head SHA is missing or malformed.")

    gates["development_ci_verified"] = bool(
        gates["head_sha_valid"]
        and ci_run
        and ci_run.get("status") == "completed"
        and ci_run.get("conclusion") == "success"
        and ci_run.get("head_sha") == head_sha
    )
    if not gates["development_ci_verified"]:
        reasons.append("Development CI has not completed successfully on the exact PR head.")

    gates["security_audit_verified"] = bool(
        gates["head_sha_valid"]
        and security_run
        and security_run.get("status") == "completed"
        and security_run.get("conclusion") == "success"
        and security_run.get("head_sha") == head_sha
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
    result = evaluate_post_merge(
        capability_id=capability_id,
        merged_main_sha=merged_main_sha,
        exact_head_ci_run=ci,
        exact_head_security_run=security,
    )
    result["ci_run_id"] = ci.get("id") if ci else None
    result["security_run_id"] = security.get("id") if security else None
    result["ci_head_sha"] = ci.get("head_sha") if ci else None
    result["security_head_sha"] = security.get("head_sha") if security else None
    return result



def open_capability_prs(repository: str, capability_id: str) -> list[dict[str, Any]]:
    """Return currently open PRs in the canonical capability lane for one capability."""
    payload = _gh_json(
        repository,
        "/pulls?state=open&base=main&per_page=100",
    )
    if not isinstance(payload, list):
        raise PromotionError("GitHub pull request query returned a non-list payload")
    data = load_inventory()
    owners: set[int] = set()
    for item in data.get("capabilities", []):
        if item.get("id") != capability_id:
            continue
        for ref in item.get("references", []):
            if (
                ref.get("type") == "pr"
                and str(ref.get("state", "")).startswith("open")
                and isinstance(ref.get("number"), int)
            ):
                owners.add(int(ref["number"]))

    matches = []
    for pr in payload:
        if not isinstance(pr, dict):
            continue
        if pr.get("number") in owners or (
            pr.get("base", {}).get("ref") == "main"
            and str(pr.get("head", {}).get("ref", "")).startswith("feat/")
            and capability_id in str(pr.get("title", "")).lower().replace(" ", "_")
        ):
            matches.append(pr)
    return matches


def inspect_capability_lifecycle(
    repository: str,
    *,
    capability_id: str,
    current_main_sha: str,
    require_review: bool = False,
) -> dict[str, Any]:
    """Select the one capability lifecycle state without dispatching duplicate work."""
    data = load_inventory()
    capability = next(
        (item for item in data.get("capabilities", []) if item.get("id") == capability_id),
        None,
    )
    if capability is None:
        raise PromotionError(f"unknown capability {capability_id}")

    owned_numbers = [
        ref["number"]
        for ref in capability.get("references", [])
        if ref.get("type") == "pr"
        and isinstance(ref.get("number"), int)
        and ref.get("role") != "integration_batch"
    ]

    observed: list[dict[str, Any]] = []
    for number in owned_numbers:
        observed.append(_pr(repository, int(number)))

    open_prs = [pr for pr in observed if str(pr.get("state", "")).lower() == "open"]
    if len(open_prs) > 1:
        raise PromotionError(
            f"{capability_id} has multiple open canonical capability PRs: "
            + ", ".join(str(pr.get("number")) for pr in open_prs)
        )
    if open_prs:
        pr = open_prs[0]
        evaluation = evaluate_promotion(
            pr,
            capability_id=capability_id,
            current_main_sha=current_main_sha,
            ci_run=_latest_completed_success(repository, WORKFLOW_CI, str(pr.get("head", {}).get("sha") or "")),
            security_run=_latest_completed_success(repository, WORKFLOW_SECURITY, str(pr.get("head", {}).get("sha") or "")),
            require_review=require_review,
        )
        return {
            "state": "IMPLEMENTATION_PR",
            "capability_id": capability_id,
            "pr": {
                "number": pr.get("number"),
                "head_sha": pr.get("head", {}).get("sha"),
                "base_sha": pr.get("base", {}).get("sha"),
            },
            "promotion": evaluation,
        }

    merged_prs = [
        pr for pr in observed
        if str(pr.get("state", "")).lower() == "closed" and pr.get("merged_at")
    ]
    if merged_prs:
        merged_pr = max(
            merged_prs,
            key=lambda pr: str(pr.get("merged_at") or ""),
        )
        merge_sha = str(merged_pr.get("merge_commit_sha") or "")
        if not merge_sha:
            raise PromotionError(f"{capability_id} has a merged PR without a merge commit SHA")
        post = inspect_post_merge(
            repository,
            capability_id=capability_id,
            merged_main_sha=merge_sha,
        )
        post["pr_number"] = merged_pr.get("number")
        post["current_main_sha"] = current_main_sha
        if post["state"] == "BOOKKEEPING_READY" and merge_sha != current_main_sha:
            post["state"] = "BLOCKED_STALE_MAIN"
            post["reasons"] = [
                "merged capability commit is no longer the current main head; reconcile before canonical bookkeeping"
            ]
        return {
            "state": "POST_MERGE",
            "capability_id": capability_id,
            "merged_pr_number": merged_pr.get("number"),
            "merged_main_sha": merge_sha,
            "post_merge": post,
        }

    return {
        "state": "READY_TO_IMPLEMENT",
        "capability_id": capability_id,
    }



def inspect_worker_result_lifecycle(
    repository: str,
    *,
    capability_id: str,
    packet: Mapping[str, Any],
    worker_result: Mapping[str, Any],
    current_main_sha: str,
    require_review: bool = False,
) -> dict[str, Any]:
    """Bind a submitted PR to the exact worker packet before promotion inspection."""
    status = str(worker_result.get("status") or "").lower()
    if status not in {"submitted", "proposed"}:
        return {
            "state": "WORKER_NOT_SUBMITTED",
            "capability_id": capability_id,
            "worker_status": status or "missing",
        }

    pr_number = worker_result.get("pr_number")
    branch = worker_result.get("branch")
    if not isinstance(pr_number, int) or pr_number < 1:
        raise PromotionError("worker result submitted without a valid PR number")
    if not isinstance(branch, str) or not branch.startswith("feat/"):
        raise PromotionError("worker result submitted without a canonical feature branch")

    pr = _pr(repository, pr_number)
    if pr.get("base", {}).get("ref") != "main":
        raise PromotionError("worker-created capability PR does not target canonical main")
    if pr.get("head", {}).get("ref") != branch:
        raise PromotionError("worker result branch does not match live PR head branch")

    expected_base = packet.get("repository", {}).get("base_sha_claim")
    if not isinstance(expected_base, str) or len(expected_base) != 40:
        raise PromotionError("worker packet lacks an exact base SHA claim")
    if pr.get("base", {}).get("sha") != expected_base:
        raise PromotionError("worker-created PR base SHA does not match the packet claim")

    changed = _gh_json(repository, f"/pulls/{pr_number}/files?per_page=100")
    if not isinstance(changed, list):
        raise PromotionError("GitHub PR file listing returned a non-list payload")

    allowed = [str(path).replace("\\", "/").rstrip("/") for path in packet.get("constraints", {}).get("allowed_path_prefixes", [])]
    forbidden = {
        str(path).replace("\\", "/").rstrip("/")
        for path in packet.get("constraints", {}).get("forbidden_paths", [])
    }

    def allowed_path(path: str) -> bool:
        normalized = path.replace("\\", "/").lstrip("./")
        if normalized in forbidden:
            return False
        return any(normalized == prefix or normalized.startswith(prefix + "/") for prefix in allowed)

    unexpected = [
        str(item.get("filename"))
        for item in changed
        if not isinstance(item, dict) or not allowed_path(str(item.get("filename", "")))
    ]
    if unexpected:
        raise PromotionError(
            "worker-created PR touches files outside the assigned capability boundary: "
            + ", ".join(unexpected[:10])
        )

    evaluation = inspect_promotion(
        repository,
        pr_number,
        current_main_sha=current_main_sha,
        require_review=require_review,
    )
    return {
        "state": "IMPLEMENTATION_PR",
        "capability_id": capability_id,
        "pr": {
            "number": pr_number,
            "branch": branch,
            "head_sha": pr.get("head", {}).get("sha"),
            "base_sha": pr.get("base", {}).get("sha"),
        },
        "promotion": evaluation,
    }



def find_worker_handoff(
    repository: str,
    *,
    capability_id: str,
    current_main_sha: str,
) -> dict[str, Any] | None:
    """Find an open worker-created PR for the next capability without trusting its content."""
    payload = _gh_json(
        repository,
        "/pulls?state=open&base=main&per_page=100",
    )
    if not isinstance(payload, list):
        raise PromotionError("GitHub pull request query returned a non-list payload")

    matches: list[dict[str, Any]] = []
    for pr in payload:
        if not isinstance(pr, dict):
            continue
        if not str(pr.get("head", {}).get("ref", "")).startswith("feat/"):
            continue
        body = str(pr.get("body") or "")
        capability = re.search(r"(?m)^- capability:\\s*([a-z0-9][a-z0-9_.-]*)\\s*$", body)
        request = re.search(r"(?m)^- worker_request_id:\\s*([A-Za-z0-9_.:-]{8,128})\\s*$", body)
        base = re.search(r"(?m)^- base_sha:\\s*([0-9a-f]{40})\\s*$", body)
        expected_prefix = "feat/" + capability_id + "-"
        if (
            capability
            and capability.group(1) == capability_id
            and request
            and base
            and str(pr.get("head", {}).get("ref", "")).startswith(expected_prefix)
        ):
            matches.append({
                **pr,
                "_worker_capability_id": capability.group(1),
                "_worker_request_id": request.group(1),
                "_worker_base_sha": base.group(1),
                "_worker_base_is_current": base.group(1) == current_main_sha,
            })

    if len(matches) > 1:
        raise PromotionError(
            f"{capability_id} has multiple open worker handoffs: "
            + ", ".join(str(item.get("number")) for item in matches)
        )
    return matches[0] if matches else None



def find_worker_handoff_history(
    repository: str,
    *,
    capability_id: str,
) -> list[dict[str, Any]]:
    """Find historical worker-generated capability PRs for one capability."""
    payload = _gh_json(
        repository,
        "/pulls?state=closed&base=main&per_page=100&sort=updated&direction=desc",
    )
    if not isinstance(payload, list):
        raise PromotionError("GitHub pull request history returned a non-list payload")
    matches: list[dict[str, Any]] = []
    expected_prefix = "feat/" + capability_id + "-"
    for pr in payload:
        if not isinstance(pr, dict):
            continue
        if not str(pr.get("head", {}).get("ref", "")).startswith(expected_prefix):
            continue
        body = str(pr.get("body") or "")
        capability = re.search(r"(?m)^- capability:\s*([a-z0-9][a-z0-9_.-]*)\s*$", body)
        request = re.search(r"(?m)^- worker_request_id:\s*([A-Za-z0-9_.:-]{8,128})\s*$", body)
        base = re.search(r"(?m)^- base_sha:\s*([0-9a-f]{40})\s*$", body)
        if capability and capability.group(1) == capability_id and request and base:
            matches.append({
                **pr,
                "_worker_capability_id": capability.group(1),
                "_worker_request_id": request.group(1),
                "_worker_base_sha": base.group(1),
            })
    return matches


def inspect_merged_worker_handoff(
    repository: str,
    *,
    capability_id: str,
    current_main_sha: str,
) -> dict[str, Any] | None:
    """Inspect the newest merged worker handoff, without requiring inventory bookkeeping first."""
    history = find_worker_handoff_history(repository, capability_id=capability_id)
    merged = [
        pr for pr in history
        if pr.get("merged_at")
        and pr.get("merge_commit_sha")
        and pr.get("base", {}).get("ref") == "main"
    ]
    if not merged:
        return None
    merged.sort(key=lambda pr: str(pr.get("merged_at") or ""), reverse=True)
    pr = merged[0]
    merge_sha = str(pr.get("merge_commit_sha") or "")
    head_sha = str(pr.get("head", {}).get("sha") or "")
    post = inspect_post_merge(
        repository,
        capability_id=capability_id,
        merged_main_sha=merge_sha,
    )
    post["current_main_sha"] = current_main_sha
    post["pr_number"] = pr.get("number")
    post["pr_head_sha"] = head_sha
    if merge_sha != current_main_sha and post["state"] == "BOOKKEEPING_READY":
        post["state"] = "BLOCKED_STALE_MAIN"
        post["reasons"] = [
            "merged worker capability is not the current main head; reconcile before canonical bookkeeping"
        ]
    return {
        "state": "POST_MERGE",
        "capability_id": capability_id,
        "merged_main_sha": merge_sha,
        "pr_number": pr.get("number"),
        "pr": {
            "number": pr.get("number"),
            "head_sha": head_sha,
            "base_sha": pr.get("base", {}).get("sha"),
        },
        "post_merge": post,
    }

def inspect_worker_handoff_pr(
    repository: str,
    *,
    capability_id: str,
    packet: Mapping[str, Any],
    handoff: Mapping[str, Any],
    current_main_sha: str,
    require_review: bool = False,
) -> dict[str, Any]:
    """Validate a worker-created PR directly from its signed handoff metadata."""
    expected_request = packet.get("request_id")
    expected_base = packet.get("repository", {}).get("base_sha_claim")
    handoff_request = handoff.get("_worker_request_id")
    handoff_base = handoff.get("_worker_base_sha")
    if handoff_request != expected_request:
        raise PromotionError("worker handoff request id does not match deterministic packet identity")
    if handoff_base != expected_base:
        raise PromotionError("worker handoff base SHA does not match deterministic packet identity")

    pr_number = handoff.get("number")
    if not isinstance(pr_number, int):
        raise PromotionError("worker handoff has no valid PR number")

    live_pr = _pr(repository, pr_number)
    if live_pr.get("head", {}).get("sha") != handoff.get("head", {}).get("sha"):
        raise PromotionError("worker handoff PR head changed after handoff discovery")
    if live_pr.get("base", {}).get("sha") != current_main_sha:
        return {
            "state": "STALE_WORKER_HANDOFF",
            "capability_id": capability_id,
            "pr": {
                "number": pr_number,
                "head_sha": live_pr.get("head", {}).get("sha"),
                "base_sha": live_pr.get("base", {}).get("sha"),
            },
            "reasons": ["worker PR base is no longer the current canonical main SHA; rebase/reconciliation is required"],
        }

    allowed = [
        str(path).replace("\\", "/").rstrip("/")
        for path in packet.get("constraints", {}).get("allowed_path_prefixes", [])
    ]
    forbidden = {
        str(path).replace("\\", "/").rstrip("/")
        for path in packet.get("constraints", {}).get("forbidden_paths", [])
    }
    changed = _gh_json(repository, f"/pulls/{pr_number}/files?per_page=100")
    if not isinstance(changed, list):
        raise PromotionError("GitHub PR file listing returned a non-list payload")
    unexpected = []
    for item in changed:
        filename = str(item.get("filename", "")).replace("\\", "/").lstrip("./")
        if filename in forbidden or not any(filename == prefix or filename.startswith(prefix + "/") for prefix in allowed):
            unexpected.append(filename)
    if unexpected:
        return {
            "state": "BLOCKED_FILE_BOUNDARY",
            "capability_id": capability_id,
            "pr": {"number": pr_number, "head_sha": live_pr.get("head", {}).get("sha")},
            "reasons": ["worker PR touches files outside assigned capability boundary: " + ", ".join(unexpected[:10])],
        }

    return {
        "state": "IMPLEMENTATION_PR",
        "capability_id": capability_id,
        "pr": {
            "number": pr_number,
            "branch": live_pr.get("head", {}).get("ref"),
            "head_sha": live_pr.get("head", {}).get("sha"),
            "base_sha": live_pr.get("base", {}).get("sha"),
        },
        "promotion": inspect_promotion(
            repository,
            pr_number,
            current_main_sha=current_main_sha,
            require_review=require_review,
        ),
    }
