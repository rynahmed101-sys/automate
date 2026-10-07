"""One bounded autonomous development cycle.

The scheduler is the operator of this state machine. Human selection of individual
capabilities is deliberately outside this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import os
import subprocess

from automate.dev.bookkeeping import create_bookkeeping_pr
from automate.dev.inventory import InventoryError
from automate.dev.prmgr import create_worker_pr
from automate.dev.publisher import build_worker_commit, push_worker_branch
from automate.dev.research import build_mirror_research_job
from automate.dev.supervisor import supervisor_snapshot
from automate.dev.worker import validate_worker_result
from automate.dev.worker_client import WorkerTransportError, dispatch_worker, wait_worker_job


class AutonomousCycleError(RuntimeError):
    """Raised when the autonomous cycle cannot complete safely."""


def _github_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise AutonomousCycleError("GH_TOKEN or GITHUB_TOKEN is required for autonomous GitHub promotion")
    return env


def _workflow_success(repository: str, workflow_file: str, commit_sha: str) -> bool:
    result = subprocess.run(
        [
            "gh", "run", "list", "--repo", repository, "--workflow", workflow_file,
            "--commit", commit_sha, "--status", "completed", "--limit", "20",
            "--json", "databaseId,conclusion",
        ],
        capture_output=True, text=True, check=False, env=_github_env(),
    )
    if result.returncode != 0:
        return False
    try:
        runs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return any(isinstance(run, dict) and run.get("conclusion") == "success" for run in runs)


def _exact_pr_evidence(repository: str, head_sha: str) -> bool:
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/actions/runs?head_sha={head_sha}&per_page=100"],
        capture_output=True, text=True, check=False, env=_github_env(),
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return False
    required = {"Automate CI", "Security Audit"}
    successful = {
        str(run.get("name"))
        for run in payload.get("workflow_runs", [])
        if run.get("head_sha") == head_sha
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    }
    return required <= successful


def promote_worker_pr(repository: str, pr_number: int, head_sha: str) -> dict[str, Any]:
    """Merge a governed PR only when its immutable head has exact CI + security evidence."""
    if os.getenv("AUTOMATE_AUTO_PROMOTE", "1").strip().lower() not in {"1", "true", "yes"}:
        return {"status": "promotion_disabled_by_governance", "pr_number": pr_number, "head_sha": head_sha}
    if len(head_sha) != 40:
        raise AutonomousCycleError("worker promotion requires an exact head SHA")
    if not _exact_pr_evidence(repository, head_sha):
        return {
            "status": "waiting_for_exact_head_evidence",
            "pr_number": pr_number,
            "head_sha": head_sha,
        }

    result = subprocess.run(
        [
            "gh", "pr", "merge", str(pr_number), "--repo", repository,
            "--merge", "--delete-branch=false", "--match-head-commit", head_sha,
        ],
        capture_output=True, text=True, check=False, env=_github_env(),
    )
    if result.returncode != 0:
        return {
            "status": "waiting_for_mergeability",
            "pr_number": pr_number,
            "head_sha": head_sha,
            "error": result.stderr.strip() or result.stdout.strip(),
        }
    return {
        "status": "merged",
        "pr_number": pr_number,
        "head_sha": head_sha,
        "output": result.stdout.strip(),
    }


def run_autonomous_cycle(
    repository: str,
    *,
    worker_url: str | None = None,
    worker_token: str | None = None,
    execute_worker: bool = False,
    local_root: Path | None = None,
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)

    if decision.get("action") == "promote_bookkeeping_pr":
        if os.getenv("AUTOMATE_AUTO_BOOKKEEP", "1").strip().lower() not in {"1", "true", "yes"}:
            return {"status": "bookkeeping_promotion_disabled_by_governance", "decision": decision}
        if not isinstance(decision.get("pr_number"), int) or not isinstance(decision.get("head_sha"), str):
            raise AutonomousCycleError("bookkeeping promotion decision is missing PR identity")
        promotion = promote_worker_pr(repository, decision["pr_number"], decision["head_sha"])
        return {"status": "bookkeeping_promotion", "decision": decision, "promotion": promotion}

    if decision.get("action") == "create_bookkeeping":
        if os.getenv("AUTOMATE_AUTO_BOOKKEEP", "1").strip().lower() not in {"1", "true", "yes"}:
            return {"status": "bookkeeping_disabled_by_governance", "decision": decision}
        if local_root is None:
            return {"status": "waiting_for_local_root", "decision": decision}
        result = create_bookkeeping_pr(
            repository,
            root=local_root,
            capability_id=str(decision["capability_id"]),
            worker_pr=decision["worker_pr"],
        )
        return {"status": "bookkeeping", "decision": decision, "bookkeeping": result}

    if decision.get("action") == "promote_worker_pr":
        if not isinstance(decision.get("pr_number"), int) or not isinstance(decision.get("head_sha"), str):
            raise AutonomousCycleError("promotion decision is missing PR identity")
        promotion = promote_worker_pr(repository, decision["pr_number"], decision["head_sha"])
        return {"status": "promotion", "decision": decision, "promotion": promotion}

    if not decision["can_dispatch"]:
        return {"status": "stopped", "decision": decision}

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }

    mirror_enabled = os.getenv(
        "AUTOMATE_MIRROR_DISCOVERY_ENABLED",
        os.getenv("AUTOMATE_EXTERNAL_RESEARCH_ENABLED", ""),
    ).strip().lower() in {"1", "true", "yes"}
    mirror_endpoint = os.getenv(
        "MIRROR_AUTONOMOUS_DISCOVERY_ENDPOINT",
        os.getenv("MIRROR_RESEARCH_ENDPOINT", ""),
    ).strip()

    research_dispatch: dict[str, Any] = {"status": "disabled_by_governance"}
    if mirror_enabled:
        if not mirror_endpoint:
            raise AutonomousCycleError(
                "MIRROR_AUTONOMOUS_DISCOVERY_ENDPOINT is required when Mirror discovery is enabled"
            )
        research_job = build_mirror_research_job(
            capability=capability_item,
            mirror_endpoint=mirror_endpoint,
            request_id="res_" + hashlib.sha256(
                (
                    capability_item["id"]
                    + "|"
                    + str(packet["packet"]["repository"].get("base_sha_claim"))
                    + "|mirror-discovery"
                ).encode()
            ).hexdigest()[:32],
            correlation_id=packet["packet"]["request_id"],
        )
        try:
            research_dispatch = dispatch_worker(
                research_job,
                url=worker_url,
                token=worker_token,
                execute=execute_worker,
            )
        except WorkerTransportError as exc:
            raise AutonomousCycleError("Mirror research commission failed: " + str(exc)) from exc

        if not execute_worker:
            return {
                "status": "research_dispatched",
                "decision": decision,
                "research": research_dispatch,
                "next_step": "the next bounded cycle will consume the durable research job before implementation dispatch",
            }

        research_execution = research_dispatch.get("execution", {})
        research_result = research_execution.get("result")
        research_job_id = research_execution.get("jobId") or research_dispatch.get("queued", {}).get("jobId")
        if not isinstance(research_result, dict) and isinstance(research_job_id, str):
            try:
                completed = wait_worker_job(
                    research_job_id,
                    url=worker_url,
                    token=worker_token,
                    timeout=300.0,
                )
            except WorkerTransportError as exc:
                return {
                    "status": "research_queued",
                    "decision": decision,
                    "research": research_dispatch,
                    "next_step": "poll the durable Mirror research job again",
                    "error": str(exc),
                }
            research_result = completed.get("job", {}).get("result")
            research_dispatch["execution"] = {**research_execution, "polled": completed}

        if not isinstance(research_result, dict):
            raise AutonomousCycleError("Mirror research execution returned no persisted result")

        packet["packet"].setdefault("context", {"files": [], "notes": []})
        packet["packet"]["context"].setdefault("notes", []).append(
            "UNTRUSTED_EXTERNAL_EVIDENCE: durable Mirror research receipt "
            + str(research_job_id or "unknown")
        )

    try:
        dispatch = dispatch_worker(
            packet,
            url=worker_url,
            token=worker_token,
            execute=True,
        )
    except WorkerTransportError as exc:
        raise AutonomousCycleError(str(exc)) from exc

    output: dict[str, Any] = {
        "status": "dispatched" if not execute_worker else "worker_completed",
        "decision": decision,
        "research": research_dispatch,
        "dispatch": dispatch,
    }

    if not execute_worker:
        return output

    execution = dispatch.get("execution", {})
    result = execution.get("result")
    if not isinstance(result, dict):
        raise AutonomousCycleError("worker execution returned no worker result")

    errors = validate_worker_result(result, packet["packet"])
    if errors:
        raise AutonomousCycleError("; ".join(errors))

    if local_root is None:
        output["status"] = "validated_proposal"
        return output

    try:
        commit = build_worker_commit(packet["packet"], result, repository_root=local_root)
    except Exception as exc:
        raise AutonomousCycleError(str(exc)) from exc

    output["commit"] = commit
    if commit["status"] != "committed":
        output["status"] = commit["status"]
        return output

    if os.getenv("AUTOMATE_AUTO_PUBLISH", "1").strip().lower() not in {"1", "true", "yes"}:
        output["status"] = "committed"
        return output

    branch_name = str(commit["branch"])
    try:
        push_worker_branch(local_root, branch_name=branch_name)
        pr = create_worker_pr(
            repository,
            branch=branch_name,
            capability_id=str(capability["id"]),
            title="feat: implement " + str(capability["name"]),
            base_sha=str(packet["packet"]["repository"]["base_sha_claim"]),
            test_result=commit["tests"],
            draft=False,
        )
    except Exception as exc:
        raise AutonomousCycleError("worker publication failed: " + str(exc)) from exc

    output["publication"] = pr
    output["status"] = "submitted"
    return output
