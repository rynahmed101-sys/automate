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
    read_worker_job,
    wait_worker_job,
)
from automate.dev.learning_runtime import (
    LearningRuntimeError,
    open_learning_store,
    persist_learning_artifact,
    record_cycle_experience,
    select_learning_strategy,
    sync_remote_learning,
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
    auto_publish: bool | None = None,
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)
    learning_store = None
    learning_sync: dict[str, Any] | None = None
    selected_strategy: dict[str, Any] = {
        "strategy_id": "frontier-default",
        "source": "default",
        "confidence": "none",
        "reason": "learning disabled",
    }
    if os.getenv("AUTOMATE_LEARNING_ENABLED", "").strip().lower() in {"1", "true", "yes"}:
        try:
            learning_store = open_learning_store(os.getenv("AUTOMATE_LEARNING_DB", "data/learning.db"))
            if worker_url and worker_token:
                learning_sync = sync_remote_learning(
                    learning_store,
                    url=worker_url,
                    token=worker_token,
                    limit=100,
                )
        except Exception as exc:
            learning_sync = {"status": "unavailable", "error": str(exc)}
            learning_store = None

    if not decision["can_dispatch"]:
        return {"status": "stopped", "decision": decision, "learning_sync": learning_sync}

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }

    if learning_store is not None:
        try:
            selected_strategy = select_learning_strategy(
                learning_store,
                task_kind="capability_implementation",
                task_target=capability_item["id"],
            )
            packet["packet"].setdefault("context", {"files": [], "notes": []})
            packet["packet"]["context"].setdefault("notes", []).extend([
                "LEARNING STRATEGY: " + str(selected_strategy["strategy_id"]),
                "LEARNING SOURCE: " + str(selected_strategy.get("source", "unknown")),
            ])
            for lesson in selected_strategy.get("adopted_lessons", [])[:5]:
                packet["packet"]["context"]["notes"].append(
                    "ADOPTED LESSON: " + str(lesson.get("statement", ""))
                )
        except LearningRuntimeError as exc:
            learning_sync = {"status": "selection_unavailable", "error": str(exc)}

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
            if learning_store is not None:
                try:
                    learning = record_cycle_experience(
                        learning_store,
                        action_cycle_id=packet["packet"]["request_id"],
                        task_kind="capability_implementation",
                        task_target=capability_item["id"],
                        strategy_id=selected_strategy["strategy_id"],
                        outcome="failure",
                        observation="worker result failed Automate validation: " + "; ".join(errors),
                        revision=packet["packet"]["repository"]["base_sha_claim"],
                        evidence_refs=[{"id": str(job_id or "worker-result"), "kind": "worker_result"}],
                        failure_class="contract_schema_defect",
                        repository=repository,
                    )
                    output["learning"] = learning
                    if worker_url and worker_token:
                        persist_learning_artifact(
                            learning["experience"],
                            artifact_type="learning_experience",
                            request_id="learning_" + learning["experience_id"].removeprefix("exp_"),
                            correlation_id=packet["packet"]["request_id"],
                            source_revision=packet["packet"]["repository"]["base_sha_claim"],
                            url=worker_url,
                            token=worker_token,
                        )
                except LearningRuntimeError:
                    output["learning_persistence"] = "unavailable"
            raise AutonomousCycleError("; ".join(errors))
        if local_root is None:
            output["status"] = "validated_proposal"
            return output
        try:
            commit = build_worker_commit(packet["packet"], result, repository_root=local_root)
        except Exception as exc:
            raise AutonomousCycleError(str(exc)) from exc
        output["commit"] = commit
        if learning_store is not None:
            try:
                learning = record_cycle_experience(
                    learning_store,
                    action_cycle_id=packet["packet"]["request_id"],
                    task_kind="capability_implementation",
                    task_target=capability_item["id"],
                    strategy_id=selected_strategy["strategy_id"],
                    outcome="success",
                    observation="worker result passed validation and produced a bounded commit proposal",
                    revision=packet["packet"]["repository"]["base_sha_claim"],
                    evidence_refs=[{"id": str(job_id or "worker-result"), "kind": "worker_result"}],
                    repository=repository,
                )
                output["learning"] = learning
                if worker_url and worker_token:
                    persist_learning_artifact(
                        learning["experience"],
                        artifact_type="learning_experience",
                        request_id="learning_" + learning["experience_id"].removeprefix("exp_"),
                        correlation_id=packet["packet"]["request_id"],
                        source_revision=packet["packet"]["repository"]["base_sha_claim"],
                        url=worker_url,
                        token=worker_token,
                    )
                    for lesson in learning.get("candidate_lessons", []):
                        if isinstance(lesson, dict):
                            persist_learning_artifact(
                                lesson,
                                artifact_type="learning_lesson",
                                request_id="lesson_" + lesson["lesson_id"].removeprefix("les_"),
                                correlation_id=packet["packet"]["request_id"],
                                source_revision=packet["packet"]["repository"]["base_sha_claim"],
                                url=worker_url,
                                token=worker_token,
                            )
            except LearningRuntimeError:
                output["learning_persistence"] = "unavailable"
        publish_enabled = (
            os.getenv("AUTOMATE_AUTO_PUBLISH", "").strip().lower() in {"1", "true", "yes"}
            if auto_publish is None else auto_publish
        )
        if commit.get("status") == "committed" and local_root is not None and publish_enabled:
            from automate.dev.publisher import publish_worker_commit
            try:
                published = publish_worker_commit(
                    repository,
                    local_root,
                    packet=packet["packet"],
                    commit=commit,
                )
            except Exception as exc:
                return {
                    **output,
                    "status": "publication_failed",
                    "publication_error": str(exc),
                }
            output["publication"] = published
            output["status"] = published["status"]
        else:
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
