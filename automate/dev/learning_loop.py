"""Deterministic self-improvement loop planner.

The planner converts recorded experience and learned state into the next
bounded action. It does not perform verification or self-modification itself.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from automate.dev.learning import LearningStore


ROOT = Path(__file__).resolve().parents[2]
LOOP_SCHEMA = ROOT / "schemas/automate-learning-loop-plan-v1.json"


class LearningLoopError(ValueError):
    """Raised for invalid learning-loop inputs."""


def _validated_plan(payload: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads(LOOP_SCHEMA.read_text(encoding="utf-8"))
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
    if errors:
        raise LearningLoopError(
            "learning loop plan violates machine contract: " + "; ".join(errors)
        )
    return payload


def plan_next_learning_action(
    store: LearningStore,
    *,
    task_kind: str,
    task_target: str,
) -> dict[str, Any]:
    experiences = store.recent_experiences(
        task_kind=task_kind,
        task_target=task_target,
        limit=50,
    )
    if not experiences:
        return _validated_plan({
            "schema_version": "automate.learning_loop_plan.v1",
            "action": "ACT",
            "reason": "No prior experience exists for this task.",
            "task_kind": task_kind,
            "task_target": task_target,
            "requires_external_verification": False,
        })

    adopted_conflicts = store.lesson_conflicts()
    scoped_conflicts = [
        conflict
        for conflict in adopted_conflicts
        if conflict.get("scope", {}).get("task_kind") == task_kind
        and conflict.get("scope", {}).get("task_target") == task_target
    ]
    if scoped_conflicts:
        return _validated_plan({
            "schema_version": "automate.learning_loop_plan.v1",
            "action": "VERIFY_CONFLICT",
            "reason": "Conflicting adopted lessons share this exact scope.",
            "task_kind": task_kind,
            "task_target": task_target,
            "conflicts": scoped_conflicts,
            "requires_external_verification": True,
        })

    failure_candidates = store.failure_lesson_candidates(min_repetitions=2)
    scoped_failures = [
        lesson
        for lesson in failure_candidates
        if lesson.get("scope", {}).get("task_kind") == task_kind
        and lesson.get("scope", {}).get("task_target") == task_target
    ]
    if scoped_failures:
        return _validated_plan({
            "schema_version": "automate.learning_loop_plan.v1",
            "action": "REPRODUCE_FAILURE_PATTERN",
            "reason": "Repeated failures form a candidate lesson that requires reproduction before adoption.",
            "task_kind": task_kind,
            "task_target": task_target,
            "candidate_lessons": scoped_failures,
            "requires_external_verification": True,
        })

    success_candidates = store.success_lesson_candidates(min_repetitions=3)
    scoped_success = [
        lesson
        for lesson in success_candidates
        if lesson.get("scope", {}).get("task_kind") == task_kind
        and lesson.get("scope", {}).get("task_target") == task_target
    ]
    if scoped_success:
        return _validated_plan({
            "schema_version": "automate.learning_loop_plan.v1",
            "action": "REPLAY_STRATEGY",
            "reason": "Repeated success produced a candidate strategy lesson that should be tested against the baseline.",
            "task_kind": task_kind,
            "task_target": task_target,
            "candidate_lessons": scoped_success,
            "requires_external_verification": True,
        })

    adopted_improvements = [
        lesson
        for lesson in store.list_adopted_lessons()
        if lesson.get("lesson_type") == "system_improvement"
        and lesson.get("scope", {}).get("task_kind") == task_kind
        and lesson.get("scope", {}).get("task_target") == task_target
    ]
    if adopted_improvements:
        return _validated_plan({
            "schema_version": "automate.learning_loop_plan.v1",
            "action": "PROPOSE_SYSTEM_EVOLUTION",
            "reason": "An adopted system-improvement lesson exists and can now produce a mutable evolution proposal.",
            "task_kind": task_kind,
            "task_target": task_target,
            "lessons": [
                {"lesson_id": x["lesson_id"], "statement": x["statement"]}
                for x in adopted_improvements
            ],
            "requires_external_verification": True,
        })

    return _validated_plan({
        "schema_version": "automate.learning_loop_plan.v1",
        "action": "ACT",
        "reason": "No unresolved candidate learning action is currently available.",
        "task_kind": task_kind,
        "task_target": task_target,
        "requires_external_verification": False,
    })
