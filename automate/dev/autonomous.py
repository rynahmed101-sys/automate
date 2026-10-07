"""One bounded autonomous development cycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import uuid

from automate.dev.inventory import InventoryError
from automate.dev.learning import LearningError, LearningStore, build_experience
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
    learning_db: str | Path | None = None,
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)
    learning_store: LearningStore | None = None
    if learning_db is not None:
        try:
            learning_store = LearningStore(learning_db)
        except Exception as exc:
            raise AutonomousCycleError("learning store initialization failed: " + str(exc)) from exc

    def remember(
        outcome: str,
        *,
        task_kind: str,
        task_target: str,
        strategy_id: str,
        observation: str,
        failure_class: str | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
    ) -> str | None:
        if learning_store is None:
            return None
        try:
            packet_id = (
                str(decision.get("worker_packet", {}).get("packet", {}).get("request_id"))
                if isinstance(decision.get("worker_packet"), dict)
                else ""
            )
            cycle_id = packet_id or (
                "cycle:" + repository + ":" + task_target + ":" + outcome
            )
            experience = build_experience(
                action_cycle_id=cycle_id,
                outcome=outcome,
                task_kind=task_kind,
                task_target=task_target,
                strategy_id=strategy_id,
                strategy_name=strategy_id,
                observation=observation,
                evidence_refs=evidence_refs or [],
                failure_class=failure_class,
                repository=repository,
                revision=(
                    decision.get("worker_packet", {})
                    .get("packet", {})
                    .get("repository", {})
                    .get("base_sha_claim")
                ),
                correlation_id=cycle_id,
                reproducible=outcome != "unknown",
            )
            return learning_store.add_experience(experience)
        except LearningError as exc:
            raise AutonomousCycleError("learning record rejected: " + str(exc)) from exc

    if not decision["can_dispatch"]:
        experience_id = remember(
            "unknown",
            task_kind="autonomous_cycle",
            task_target=str(decision.get("action") or "control_plane"),
            strategy_id="frontier-default",
            observation="supervisor withheld dispatch because the current control-plane state was not dispatchable",
            failure_class="integration_defect" if decision.get("action") == "stop" else None,
        )
        if learning_store is not None:
            learning_store.close()
        return {
            "status": "stopped",
            "decision": decision,
            "experience_id": experience_id,
        }

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }
    selected_strategy = (
        learning_store.select_strategy(
            task_kind="capability_implementation",
            task_target=capability_item["id"],
        )
        if learning_store is not None
        else {
            "strategy_id": "frontier-default",
            "source": "disabled",
            "confidence": "none",
            "reason": "learning store not configured",
        }
    )
    if selected_strategy.get("adopted_lessons"):
        packet["packet"].setdefault("context", {"files": [], "notes": []})
        packet["packet"]["context"].setdefault("notes", [])
        packet["packet"]["context"]["notes"].append(
            "Selected adopted learning strategy: "
            + str(selected_strategy["strategy_id"])
        )
        for lesson in selected_strategy["adopted_lessons"][:10]:
            packet["packet"]["context"]["notes"].append(
                "ADOPTED LESSON [" + str(lesson.get("lesson_id", "unknown")) + "]: "
                + str(lesson.get("statement", ""))
            )

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
            experience_id = remember(
                "unknown",
                task_kind="capability_implementation",
                task_target=capability_item["id"],
                strategy_id=selected_strategy["strategy_id"],
                observation="bounded research was dispatched but execution was intentionally deferred",
                evidence_refs=[{"id": str(research_dispatch.get("queued", {}).get("jobId") or "research-dispatch"), "kind": "research_job"}],
            )
            if learning_store is not None:
                learning_store.close()
            return {
                "status": "research_dispatched",
                "decision": decision,
                "research": research_dispatch,
                "learning_strategy": selected_strategy,
                "experience_id": experience_id,
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
        remember(
            "failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker dispatch failed: " + str(exc),
            failure_class="integration_defect",
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError(str(exc)) from exc

    output: dict[str, Any] = {
        "status": "dispatched" if not execute_worker else "worker_completed",
        "decision": decision,
        "research": research_dispatch,
        "dispatch": dispatch,
    }

    if not execute_worker:
        experience_id = remember(
            "unknown",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker was queued but execution was intentionally deferred",
            evidence_refs=[{"id": str(dispatch.get("queued", {}).get("jobId") or "worker-dispatch"), "kind": "worker_job"}],
        )
        if learning_store is not None:
            learning_store.close()
        output["learning_strategy"] = selected_strategy
        output["experience_id"] = experience_id
        return output

    execution = dispatch.get("execution", {})
    result = execution.get("result")
    if not isinstance(result, dict):
        remember(
            "failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker execution returned no persisted worker result",
            failure_class="integration_defect",
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("worker execution returned no worker result")

    errors = validate_worker_result(result, packet["packet"])
    if errors:
        remember(
            "failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker result failed trust-boundary validation: " + "; ".join(errors),
            failure_class="contract_schema_defect",
            evidence_refs=[{"id": str(job_id if "job_id" in locals() else "worker-result"), "kind": "worker_result"}],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("; ".join(errors))

    if local_root is None:
        experience_id = remember(
            "success",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker result passed Automate validation and produced a bounded proposal",
            evidence_refs=[{"id": str(job_id if "job_id" in locals() else "worker-result"), "kind": "worker_result"}],
        )
        if learning_store is not None:
            learning_store.close()
        output["status"] = "validated_proposal"
        output["learning_strategy"] = selected_strategy
        output["experience_id"] = experience_id
        return output

    try:
        commit = build_worker_commit(
            packet["packet"],
            result,
            repository_root=local_root,
        )
    except Exception as exc:
        raise AutonomousCycleError(str(exc)) from exc

    experience_id = remember(
        "success",
        task_kind="capability_implementation",
        task_target=capability_item["id"],
        strategy_id=selected_strategy["strategy_id"],
        observation="validated worker result was converted into a bounded local commit proposal",
        evidence_refs=[{"id": str(job_id if "job_id" in locals() else "worker-result"), "kind": "worker_result"}],
    )
    if learning_store is not None:
        learning_store.close()
    output["commit"] = commit
    output["status"] = commit["status"]
    output["learning_strategy"] = selected_strategy
    output["experience_id"] = experience_id
    return output
