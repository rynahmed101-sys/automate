"""One bounded autonomous development cycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import uuid

from automate.dev.inventory import InventoryError
from automate.dev.learning import LearningError, LearningStore, build_experience
from automate.dev.learning_client import submit_learning_artifact, sync_learning_store
from automate.dev.learning_loop import plan_next_learning_action
from automate.dev.learning_model import LearningModelError, generate_candidate_lessons
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
    learning_sync: dict[str, Any] | None = None
    if learning_db is not None:
        learning_store = LearningStore(learning_db)
        if os.getenv("AUTOMATE_LEARNING_ENDPOINT") and os.getenv("AUTOMATE_LEARNING_TOKEN"):
            try:
                learning_sync = sync_learning_store(learning_store, limit=100)
            except Exception as exc:
                learning_sync = {"status": "unavailable", "error": str(exc)}

    def remember(
        outcome: str,
        *,
        task_kind: str,
        task_target: str,
        strategy_id: str,
        observation: str,
        evidence_refs: list[dict[str, Any]] | None = None,
        failure_class: str | None = None,
    ) -> str | None:
        if learning_store is None:
            return None
        cycle_id = (
            str(decision.get("worker_packet", {}).get("packet", {}).get("request_id"))
            if isinstance(decision.get("worker_packet"), dict)
            else ""
        ) or f"cycle:{repository}:{task_target}:{strategy_id}:{outcome}"
        try:
            exp = build_experience(
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
                revision=str(
                    decision.get("worker_packet", {})
                    .get("packet", {})
                    .get("repository", {})
                    .get("base_sha_claim") or ""
                ) or None,
                correlation_id=cycle_id,
                reproducible=outcome != "unknown",
            )
            experience_id = learning_store.add_experience(exp)

            if os.getenv("AUTOMATE_REASONING_ENDPOINT"):
                try:
                    for lesson in generate_candidate_lessons(
                        learning_store.recent_experiences(
                            task_kind=task_kind,
                            task_target=task_target,
                            limit=20,
                        ),
                        endpoint=os.getenv("AUTOMATE_REASONING_ENDPOINT"),
                    ):
                        learning_store.add_lesson(lesson)
                        if os.getenv("AUTOMATE_LEARNING_ENDPOINT") and os.getenv("AUTOMATE_LEARNING_TOKEN"):
                            try:
                                submit_learning_artifact(
                                    lesson,
                                    artifact_type="learning_lesson",
                                    request_id="lesson_" + lesson["lesson_id"].removeprefix("les_"),
                                    correlation_id=cycle_id,
                                    source_revision=exp["provenance"]["revision"],
                                    source_repo=repository,
                                    source_component="reasoning_model",
                                )
                            except Exception:
                                pass
                except LearningModelError:
                    pass

            for lesson in (
                learning_store.failure_lesson_candidates(min_repetitions=2)
                + learning_store.success_lesson_candidates(min_repetitions=3)
            ):
                learning_store.add_lesson(lesson)

            if os.getenv("AUTOMATE_LEARNING_ENDPOINT") and os.getenv("AUTOMATE_LEARNING_TOKEN"):
                try:
                    submit_learning_artifact(
                        exp,
                        artifact_type="learning_experience",
                        request_id="learning_" + experience_id.removeprefix("exp_"),
                        correlation_id=cycle_id,
                        source_revision=exp["provenance"]["revision"],
                        source_repo=repository,
                        source_component="autonomous",
                    )
                except Exception:
                    pass
            return experience_id
        except LearningError as exc:
            raise AutonomousCycleError("learning record rejected: " + str(exc)) from exc

    if not decision["can_dispatch"]:
        remember(
            "unknown",
            task_kind="autonomous_cycle",
            task_target=str(decision.get("capability_id") or "control_plane"),
            strategy_id="frontier-default",
            observation="Supervisor withheld dispatch because the current control-plane state is not dispatchable.",
            failure_class="integration_defect" if decision.get("action") == "stop" else None,
        )
        if learning_store is not None:
            learning_store.close()
        return {
            "status": "stopped",
            "decision": decision,
            "learning_sync": learning_sync,
        }

    packet = decision["worker_packet"]
    capability = packet["packet"]["capability"]
    capability_item = {
        "id": capability["id"],
        "name": capability["name"],
        "task": packet["packet"].get("task", {}),
    }

    learning_action = (
        plan_next_learning_action(
            learning_store,
            task_kind="capability_implementation",
            task_target=capability_item["id"],
        )
        if learning_store is not None
        else {
            "action": "ACT",
            "reason": "learning store not configured",
        }
    )
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

    packet["packet"].setdefault("context", {"files": [], "notes": []})
    packet["packet"]["context"].setdefault("notes", [])
    packet["packet"]["context"]["notes"].append(
        "LEARNING LOOP ACTION: " + str(learning_action["action"])
    )
    packet["packet"]["context"]["notes"].append(
        "LEARNING LOOP REASON: " + str(learning_action["reason"])
    )
    if selected_strategy.get("source") == "adopted_lesson":
        packet["packet"]["context"]["notes"].append(
            "LEARNED STRATEGY: " + str(selected_strategy["strategy_id"])
        )
        for lesson in selected_strategy.get("adopted_lessons", [])[:10]:
            packet["packet"]["context"]["notes"].append(
                "ADOPTED LESSON [" + str(lesson.get("lesson_id", "unknown")) + "]: "
                + str(lesson.get("statement", ""))
            )
            for precondition in lesson.get("preconditions", []):
                packet["packet"]["context"]["notes"].append(
                    "LESSON PRECONDITION: " + str(precondition)
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
        "learning_strategy": selected_strategy,
        "learning_action": learning_action,
        "learning_sync": learning_sync,
    }

    if not execute_worker:
        experience_id = remember(
            "unknown",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="implementation worker was queued without requesting execution",
            evidence_refs=[{"id": str(dispatch.get("queued", {}).get("jobId") or "worker-dispatch"), "kind": "worker_job"}],
        )
        if learning_store is not None:
            learning_store.close()
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
            observation="worker execution returned no worker result",
            failure_class="integration_defect",
        )
        if learning_store is not None:
            learning_store.close()
        raise AutonomousCycleError("worker execution returned no worker result")

    errors = validate_worker_result(result, packet["packet"])
    if errors:
        experience_id = remember(
            "failure",
            task_kind="capability_implementation",
            task_target=capability_item["id"],
            strategy_id=selected_strategy["strategy_id"],
            observation="worker result failed Automate validation: " + "; ".join(errors),
            evidence_refs=[{"id": str(dispatch.get("execution", {}).get("jobId") or "worker-result"), "kind": "worker_result"}],
            failure_class="contract_schema_defect",
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
            evidence_refs=[{"id": str(dispatch.get("execution", {}).get("jobId") or "worker-result"), "kind": "worker_result"}],
        )
        if learning_store is not None:
            learning_store.close()
        output["status"] = "validated_proposal"
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
        evidence_refs=[{"id": str(dispatch.get("execution", {}).get("jobId") or "worker-result"), "kind": "worker_result"}],
    )
    if learning_store is not None:
        learning_store.close()
    output["commit"] = commit
    output["status"] = commit["status"]
    output["experience_id"] = experience_id
    return output
