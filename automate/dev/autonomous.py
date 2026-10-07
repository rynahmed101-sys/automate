"""Bounded autonomous development cycle.

External world research is governance-gated. Before the 3B frontier, this cycle
must not commission open-ended research. Durable worker completion is polled
through persisted Chanfana results rather than assumed synchronous.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from automate.dev.inventory import InventoryError
from automate.dev.verification_engine import deterministic_id
from automate.dev.publisher import build_worker_commit
from automate.dev.research import build_mirror_research_job
from automate.dev.supervisor import supervisor_snapshot
from automate.dev.worker import validate_worker_result
from automate.dev.worker_client import (
    WorkerTransportError,
    dispatch_worker,
    wait_worker_job,
)


class AutonomousCycleError(RuntimeError):
    """Raised when the autonomous cycle cannot complete safely."""


def run_autonomous_cycle(
    repository: str,
    *,
    worker_url: str | None = None,
    worker_token: str | None = None,
    execute_worker: bool = False,
    local_root: Path | None = None,
    mode: Literal["backlog", "research"] = "backlog",
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)
    if not decision["can_dispatch"]:
        return {"status": "stopped", "decision": decision}

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }

    # BACKLOG mode is strictly implementation-first. It must never commission
    # open-ended Mirror research merely because the worker is being automated.
    if mode == "backlog":
        try:
            dispatch = dispatch_worker(
                packet,
                url=worker_url,
                token=worker_token,
                execute=execute_worker,
            )
        except WorkerTransportError as exc:
            raise AutonomousCycleError(str(exc)) from exc
        output: dict[str, Any] = {
            "status": "worker_dispatched",
            "decision": decision,
            "dispatch": dispatch,
            "research": None,
            "operating_mode": "BACKLOG",
        }
        queued = dispatch.get("queued", {})
        job_id = queued.get("jobId")
        job_state = str(queued.get("state") or "").lower()
        if isinstance(job_id, str) and job_state in {"succeeded", "failed", "cancelled"}:
            try:
                persisted = read_worker_job(
                    job_id,
                    url=worker_url,
                    token=worker_token,
                    include_result=True,
                )
                output["persisted_job"] = persisted
            except WorkerTransportError as exc:
                output["persisted_job_read_error"] = str(exc)
        if not execute_worker:
            return output
        execution = dispatch.get("execution", {})
        result = execution.get("result")
        job_id = execution.get("jobId") or dispatch.get("queued", {}).get("jobId")
        if not isinstance(result, dict) and isinstance(job_id, str):
            try:
                completed = wait_worker_job(
                    job_id,
                    url=worker_url,
                    token=worker_token,
                    timeout=900.0,
                )
            except WorkerTransportError as exc:
                return {
                    **output,
                    "status": "worker_queued",
                    "next_step": "poll the durable worker job again",
                    "error": str(exc),
                }
            result = completed.get("job", {}).get("result")
            output["dispatch"] = {**dispatch, "execution": {**execution, "polled": completed}}
        if not isinstance(result, dict):
            raise AutonomousCycleError("worker execution returned no persisted worker result")
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
        output["status"] = commit["status"]
        return output

    # RESEARCH mode is explicitly opt-in and remains separate from the backlog.
    research_enabled = os.getenv("AUTOMATE_EXTERNAL_RESEARCH_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not research_enabled:
        return {
            "status": "research_disabled_by_governance",
            "decision": decision,
            "next_step": "keep external research disabled until DISCOVERY_READY",
        }

    mirror_endpoint = os.getenv("MIRROR_RESEARCH_ENDPOINT", "").strip()
    if not mirror_endpoint:
        raise AutonomousCycleError("MIRROR_RESEARCH_ENDPOINT is required when external research is enabled")

    base_sha = packet["packet"]["repository"].get("base_sha_claim")
    research_job = build_mirror_research_job(
        capability=capability_item,
        mirror_endpoint=mirror_endpoint,
        request_id=deterministic_id(
            "res", capability_item["id"], base_sha, "external_research"
        ),
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
            "next_step": "poll the durable research job and reconcile its evidence",
        }

    execution = research_dispatch.get("execution", {})
    research_result = execution.get("result")
    job_id = execution.get("jobId") or research_dispatch.get("queued", {}).get("jobId")
    if not isinstance(research_result, dict) and isinstance(job_id, str):
        try:
            completed = wait_worker_job(
                job_id,
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
        research_dispatch["execution"] = {**execution, "polled": completed}

    if not isinstance(research_result, dict):
        raise AutonomousCycleError("Mirror research execution returned no persisted result")

    # Do not truncate or reinterpret the research result. Pass only a durable
    # reference into the worker context; the receipt remains Chanfana-owned.
    packet["packet"].setdefault("context", {"files": [], "notes": []})
    packet["packet"]["context"].setdefault("notes", []).append(
        "Untrusted Mirror research receipt is available through durable job "
        + str(job_id or "unknown")
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
        "status": "worker_dispatched",
        "decision": decision,
        "research": research_dispatch,
        "dispatch": dispatch,
    }

    if not execute_worker:
        return output

    execution = dispatch.get("execution", {})
    result = execution.get("result")
    job_id = execution.get("jobId") or dispatch.get("queued", {}).get("jobId")
    if not isinstance(result, dict) and isinstance(job_id, str):
        try:
            completed = wait_worker_job(
                job_id,
                url=worker_url,
                token=worker_token,
                timeout=900.0,
            )
        except WorkerTransportError as exc:
            return {
                **output,
                "status": "worker_queued",
                "next_step": "poll the durable worker job again",
                "error": str(exc),
            }
        result = completed.get("job", {}).get("result")
        output["dispatch"] = {**dispatch, "execution": {**execution, "polled": completed}}

    if not isinstance(result, dict):
        raise AutonomousCycleError("worker execution returned no persisted worker result")

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
    output["status"] = commit["status"]
    return output
