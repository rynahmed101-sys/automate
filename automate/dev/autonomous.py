"""One bounded autonomous development cycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import uuid

from automate.dev.inventory import InventoryError
from automate.dev.publisher import build_worker_commit
from automate.dev.research import build_mirror_research_job
from automate.dev.supervisor import supervisor_snapshot
from automate.dev.worker import validate_worker_result
from automate.dev.worker_client import WorkerTransportError, dispatch_worker, wait_worker_job


class AutonomousCycleError(RuntimeError):
    """Raised when the autonomous cycle cannot complete safely."""


def run_autonomous_cycle(
    repository: str,
    *,
    worker_url: str | None = None,
    worker_token: str | None = None,
    execute_worker: bool = False,
    local_root: Path | None = None,
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)
    if not decision["can_dispatch"]:
        return {
            "status": "stopped",
            "decision": decision,
        }

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }

    external_research_enabled = os.getenv("AUTOMATE_EXTERNAL_RESEARCH_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    research_dispatch: dict[str, Any] = {"status": "disabled_by_governance"}
    if external_research_enabled:
        mirror_endpoint = os.getenv("MIRROR_RESEARCH_ENDPOINT", "").strip()
        if not mirror_endpoint:
            raise AutonomousCycleError("MIRROR_RESEARCH_ENDPOINT is required when external research is enabled")
        research_job = build_mirror_research_job(
            capability=capability_item,
            mirror_endpoint=mirror_endpoint,
            request_id="res_" + __import__("hashlib").sha256(
                (capability_item["id"] + "|" + str(packet["packet"]["repository"].get("base_sha_claim")) + "|external_research").encode()
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
            raise AutonomousCycleError("research commission failed: " + str(exc)) from exc

        if not execute_worker:
            return {
                "status": "research_dispatched",
                "decision": decision,
                "research": research_dispatch,
                "next_step": "consume research evidence and then dispatch the implementation worker",
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
                    "next_step": "poll the durable research job again",
                    "error": str(exc),
                }
            research_result = completed.get("job", {}).get("result")
            research_dispatch["execution"] = {**research_execution, "polled": completed}

        if not isinstance(research_result, dict):
            raise AutonomousCycleError("Mirror research execution returned no persisted result")

        packet["packet"].setdefault("context", {"files": [], "notes": []})
        packet["packet"]["context"].setdefault("notes", []).append(
            "Untrusted Mirror research receipt is available through durable job "
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
        commit = build_worker_commit(
            packet["packet"],
            result,
            repository_root=local_root,
        )
    except Exception as exc:
        raise AutonomousCycleError(str(exc)) from exc

    output["commit"] = commit
    output["status"] = commit["status"]
    return output
