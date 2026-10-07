"""Normalize verification, CI, reconciliation, and worker outcomes into learning experience."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from automate.dev.learning import LearningStore, build_experience
from automate.dev.diagnostics import diagnose_failure


def _outcome_from_state(state: str) -> str:
    normalized = str(state).upper()
    if normalized == "VERIFIED":
        return "success"
    if normalized in {"CONTRADICTED", "FALSE"}:
        return "contradiction"
    if normalized in {"BLOCKED", "UNRESOLVED", "QUARANTINED", "UNVERIFIED"}:
        return "unknown"
    return "failure"


def record_system_experience(
    store: LearningStore,
    *,
    action_cycle_id: str,
    task_kind: str,
    task_target: str,
    strategy_id: str,
    observation: str,
    outcome: str,
    revision: str | None = None,
    repository: str = "rynahmed101-sys/automate",
    evidence_refs: Iterable[Mapping[str, Any]] = (),
    failure_class: str | None = None,
    correlation_id: str | None = None,
) -> str:
    derived_failure_class = failure_class
    if outcome in {"failure", "contradiction"} and not derived_failure_class:
        diagnoses = diagnose_failure(
            message=observation,
            evidence_kinds=[
                str(ref.get("kind", ""))
                for ref in evidence_refs
                if isinstance(ref, Mapping)
            ],
        )
        if diagnoses:
            derived_failure_class = str(diagnoses[0]["failure_class"])

    experience = build_experience(
        action_cycle_id=action_cycle_id,
        outcome=outcome,
        task_kind=task_kind,
        task_target=task_target,
        strategy_id=strategy_id,
        strategy_name=strategy_id,
        observation=observation,
        evidence_refs=list(evidence_refs),
        failure_class=derived_failure_class,
        repository=repository,
        revision=revision,
        correlation_id=correlation_id or action_cycle_id,
        reproducible=outcome != "unknown",
    )
    return store.add_experience(experience)


def record_ci_result(
    store: LearningStore,
    *,
    action_cycle_id: str,
    task_target: str,
    strategy_id: str,
    conclusion: str,
    run_id: str | int,
    revision: str | None = None,
    repository: str = "rynahmed101-sys/automate",
    details: str = "",
) -> str:
    conclusion = str(conclusion).lower()
    outcome = "success" if conclusion == "success" else "failure"
    if conclusion not in {"success", "failure"}:
        outcome = "unknown"
    observation = f"CI run {run_id} concluded {conclusion}." + (f" {details}" if details else "")
    return record_system_experience(
        store,
        action_cycle_id=action_cycle_id,
        task_kind="ci",
        task_target=task_target,
        strategy_id=strategy_id,
        observation=observation,
        outcome=outcome,
        revision=revision,
        repository=repository,
        evidence_refs=[{"id": str(run_id), "kind": "ci_run"}],
        failure_class="ci_environment_failure" if conclusion in {"cancelled", "timed_out"} else None,
        correlation_id=action_cycle_id,
    )


def record_reconciliation_result(
    store: LearningStore,
    *,
    action_cycle_id: str,
    task_target: str,
    strategy_id: str,
    findings: Iterable[Mapping[str, Any]],
    ready: bool,
    revision: str | None = None,
    repository: str = "rynahmed101-sys/automate",
) -> str:
    findings_list = [dict(x) for x in findings]
    if ready and not findings_list:
        outcome = "success"
    elif findings_list:
        outcome = "failure"
    else:
        outcome = "unknown"
    observation = (
        "Reconciliation completed with no findings."
        if outcome == "success"
        else "Reconciliation findings: "
        + "; ".join(str(x.get("detail", x)) for x in findings_list)
    )
    return record_system_experience(
        store,
        action_cycle_id=action_cycle_id,
        task_kind="reconciliation",
        task_target=task_target,
        strategy_id=strategy_id,
        observation=observation,
        outcome=outcome,
        revision=revision,
        repository=repository,
        evidence_refs=[
            {
                "id": f"reconciliation:{action_cycle_id}",
                "kind": "reconciliation",
                "finding_count": len(findings_list),
            }
        ],
        failure_class="stale_revision"
        if any(x.get("kind") == "stale_revision" for x in findings_list)
        else None,
        correlation_id=action_cycle_id,
    )


def record_verification_result(
    store: LearningStore,
    *,
    action_cycle_id: str,
    task_target: str,
    strategy_id: str,
    evidence_state: str,
    revision: str | None = None,
    repository: str = "rynahmed101-sys/automate",
    evidence_refs: Iterable[Mapping[str, Any]] = (),
    details: str = "",
) -> str:
    outcome = _outcome_from_state(evidence_state)
    observation = (
        f"Verification ended in evidence state {evidence_state}."
        + (f" {details}" if details else "")
    )
    return record_system_experience(
        store,
        action_cycle_id=action_cycle_id,
        task_kind="verification",
        task_target=task_target,
        strategy_id=strategy_id,
        observation=observation,
        outcome=outcome,
        revision=revision,
        repository=repository,
        evidence_refs=evidence_refs,
        failure_class="genuine_contradiction"
        if outcome == "contradiction"
        else None,
        correlation_id=action_cycle_id,
    )
