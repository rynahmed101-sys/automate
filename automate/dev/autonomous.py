"""Bounded autonomous development cycle.

External world research is governance-gated. Before the 3B frontier, this cycle
must not commission open-ended research. Durable worker completion is polled
through persisted Chanfana results rather than assumed synchronous.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from automate.dev.inventory import InventoryError
from automate.dev.learning import LearningError, LearningStore, build_experience
from automate.dev.learning_client import submit_learning_artifact, sync_learning_store
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
    learning_db: str | Path | None = None,
) -> dict[str, Any]:
    decision = supervisor_snapshot(repository, live=True)
    learning_store: LearningStore | None = None
    if learning_db is not None:
        try:
            learning_store = LearningStore(learning_db)
        except Exception as exc:
            raise AutonomousCycleError("learning store initialization failed: " + str(exc)) from exc

    remote_learning_sync: dict[str, Any] | None = None
    if learning_store is not None and os.getenv("AUTOMATE_LEARNING_ENDPOINT") and os.getenv("AUTOMATE_LEARNING_TOKEN"):
        try:
            remote_learning_sync = sync_learning_store(learning_store, limit=100)
        except Exception as exc:
            # Durable remote memory is an accelerator, not a single point of failure.
            remote_learning_sync = {"status": "unavailable", "error": str(exc)}

    def record_learning(
        *,
        outcome: str,
        task_kind: str,
        task_target: str,
        strategy_id: str,
        observation: str,
        evidence_refs: list[dict[str, Any]] | None = None,
        failure_class: str | None = None,
        correlation_id: str | None = None,
    ) -> str | None:
        if learning_store is None:
            return None
        action_cycle_id = (
            str(decision.get("worker_packet", {}).get("packet", {}).get("request_id"))
            if isinstance(decision.get("worker_packet"), dict)
            else ""
        ) or deterministic_id("cycle", repository, task_target, strategy_id, outcome)
        try:
            experience = build_experience(
                action_cycle_id=action_cycle_id,
                outcome=outcome,
                task_kind=task_kind,
                task_target=task_target,
                strategy_id=strategy_id,
                strategy_name=strategy_id,
                observation=observation,
                evidence_refs=evidence_refs or [],
                failure_class=failure_class,
                repository=repository,
                revision=str(
                    decision.get("worker_packet", {})
                    .get("packet", {})
                    .get("repository", {})
                    .get("base_sha_claim") or ""
                ) or None,
                correlation_id=correlation_id or action_cycle_id,
            )
            experience_id = learning_store.add_experience(experience)
            if os.getenv("AUTOMATE_LEARNING_ENDPOINT") and os.getenv("AUTOMATE_LEARNING_TOKEN"):
                try:
                    submit_learning_artifact(
                        experience,
                        artifact_type="learning_experience",
                        request_id="learning_" + experience_id.removeprefix("exp_"),
                        correlation_id=correlation_id or action_cycle_id,
                        source_revision=experience["provenance"]["revision"],
                        source_repo=repository,
                        source_component="autonomous",
                    )
                except Exception:
                    # Preserve local learning even if the remote transport is unavailable.
                    pass
            # Repeated observations become candidate lessons automatically, but remain
            # unverified until an independent verification path explicitly promotes them.
            for lesson in (
                learning_store.failure_lesson_candidates(min_repetitions=2)
                + learning_store.success_lesson_candidates(min_repetitions=3)
            ):
                learning_store.add_lesson(lesson)
            return experience_id
        except LearningError as exc:
            raise AutonomousCycleError("learning record rejected: " + str(exc)) from exc

    if not decision["can_dispatch"]:
        record_learning(
            outcome="unknown",
            task_kind="autonomous_cycle",
            task_target=str(decision.get("capability_id") or "control_plane"),
            strategy_id="frontier-default",
            observation="supervisor withheld dispatch because the current control-plane state was not dispatchable",
            failure_class="integration_defect" if decision.get("action") == "stop" else None,
        )
        if learning_store is not None:
            learning_store.close()
        return {"status": "stopped", "decision": decision, "learning_sync": remote_learning_sync}

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

    if remote_learning_sync is not None:
        selected_strategy["learning_sync"] = remote_learning_sync

    # External world research stays disabled by governance until the current
    # 1A-3A reconciliation/verification frontier is cleared.
    if os.getenv("AUTOMATE_EXTERNAL_RESEARCH_ENABLED", "").strip().lower() not in {"1", "true", "yes"}:
        record_learning(
            outcome="unknown",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="external research path was intentionally disabled by governance; no implementation result was inferred",
            failure_class=None,
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        return {
            "status": "research_disabled_by_governance",
            "decision": decision,
            "learning_strategy": selected_strategy,
            "next_step": "run the Verification & Reconciliation Engine against the installed backlog",
        }

    mirror_endpoint = os.getenv("MIRROR_RESEARCH_ENDPOINT", "").strip()
    if not mirror_endpoint:
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="external research was enabled but no Mirror research endpoint was configured",
            failure_class="integration_defect",
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
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
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="research commission failed: " + str(exc),
            failure_class="integration_defect",
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("research commission failed: " + str(exc)) from exc

    if not execute_worker:
        exp_id = record_learning(
            outcome="unknown",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="bounded Mirror research job was dispatched; completion was intentionally deferred",
            evidence_refs=[{"id": str(research_dispatch.get("queued", {}).get("jobId") or "research-dispatch"), "kind": "research_job"}],
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        return {
            "status": "research_dispatched",
            "decision": decision,
            "research": research_dispatch,
            "learning_strategy": selected_strategy,
            "experience_id": exp_id,
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
            record_learning(
                outcome="failure",
                task_kind="capability_implementation",
                task_target=capability_item["id"],
                strategy_id=selected_strategy["strategy_id"],
                observation="research polling failed: " + str(exc),
                failure_class="integration_defect",
                correlation_id=packet["packet"]["request_id"],
            )
            if learning_store is not None:
                learning_store.close()
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
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="Mirror research execution returned no persisted result",
            failure_class="integration_defect",
            evidence_refs=[{"id": str(job_id or "research-result"), "kind": "research_result"}],
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("Mirror research execution returned no persisted result")

    # Do not truncate or reinterpret the research result. Pass only a durable
    # reference into the worker context; the receipt remains Chanfana-owned.
    packet["packet"].setdefault("context", {"files": [], "notes": []})
    packet["packet"]["context"].setdefault("notes", []).append(
        "Untrusted Mirror research receipt is available through durable job "
        + str(job_id or "unknown")
    )
    packet["packet"]["context"]["notes"].append(
        "Selected learning strategy: " + str(selected_strategy["strategy_id"])
    )

    try:
        dispatch = dispatch_worker(
            packet,
            url=worker_url,
            token=worker_token,
            execute=True,
        )
    except WorkerTransportError as exc:
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker dispatch failed: " + str(exc),
            failure_class="integration_defect",
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
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
            record_learning(
                outcome="failure",
                task_kind="capability_implementation",
                task_target=capability_item["id"],
                strategy_id=selected_strategy["strategy_id"],
                observation="worker polling failed: " + str(exc),
                failure_class="integration_defect",
                correlation_id=packet["packet"]["request_id"],
            )
            if learning_store is not None:
                learning_store.close()
            return {
                **output,
                "status": "worker_queued",
                "learning_strategy": selected_strategy,
                "next_step": "poll the durable worker job again",
                "error": str(exc),
            }
        result = completed.get("job", {}).get("result")
        output["dispatch"] = {**dispatch, "execution": {**execution, "polled": completed}}

    if not isinstance(result, dict):
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker execution returned no persisted worker result",
            failure_class="integration_defect",
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("worker execution returned no persisted worker result")

    errors = validate_worker_result(result, packet["packet"])
    if errors:
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker result rejected by the trust boundary: " + "; ".join(errors),
            failure_class="contract_schema_defect",
            evidence_refs=[{"id": str(job_id or "worker-result"), "kind": "worker_result"}],
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("; ".join(errors))

    if local_root is None:
        exp_id = record_learning(
            outcome="success",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker result passed Automate validation and produced a bounded proposal",
            evidence_refs=[{"id": str(job_id or "worker-result"), "kind": "worker_result"}],
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        output["status"] = "validated_proposal"
        output["learning_strategy"] = selected_strategy
        output["experience_id"] = exp_id
        return output

    try:
        commit = build_worker_commit(packet["packet"], result, repository_root=local_root)
    except Exception as exc:
        record_learning(
            outcome="failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="validated worker result could not be converted into a bounded local commit proposal: " + str(exc),
            failure_class="implementation_defect",
            correlation_id=packet["packet"]["request_id"],
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError(str(exc)) from exc

    exp_id = record_learning(
        outcome="success",
        task_kind="capability_implementation",
        task_target=capability_item["id"],
        strategy_id=selected_strategy["strategy_id"],
        observation="validated worker result was converted into a bounded local commit proposal",
        evidence_refs=[{"id": str(job_id or "worker-result"), "kind": "worker_result"}],
        correlation_id=packet["packet"]["request_id"],
    )
    if learning_store is not None:
        learning_store.close()
    output["commit"] = commit
    output["status"] = commit["status"]
    output["learning_strategy"] = selected_strategy
    output["experience_id"] = exp_id
    return output
