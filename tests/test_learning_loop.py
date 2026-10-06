from pathlib import Path

from automate.dev.learning import LearningStore, build_experience, build_lesson
from automate.dev.learning_loop import plan_next_learning_action


def _exp(store, cycle, outcome, target, failure_class=None):
    exp = build_experience(
        action_cycle_id=cycle,
        outcome=outcome,
        task_kind="calculus",
        task_target=target,
        strategy_id="s",
        strategy_name="s",
        observation=outcome,
        evidence_refs=[{"id": cycle}],
        failure_class=failure_class,
        repository="test/repo",
        revision="a"*40,
        correlation_id=cycle,
        reproducible=outcome != "unknown",
    )
    store.add_experience(exp)


def test_loop_starts_with_action_when_no_history(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        result = plan_next_learning_action(store, task_kind="calculus", task_target="fresh")
        assert result["action"] == "ACT"
    finally:
        store.close()


def test_loop_prioritizes_reproduction_of_repeated_failure(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        _exp(store, "f1", "failure", "integral", "missing_assumption")
        _exp(store, "f2", "failure", "integral", "missing_assumption")
        result = plan_next_learning_action(store, task_kind="calculus", task_target="integral")
        assert result["action"] == "REPRODUCE_FAILURE_PATTERN"
        assert result["requires_external_verification"] is True
    finally:
        store.close()


def test_loop_prioritizes_strategy_replay_after_repeated_success(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        for idx in range(3):
            _exp(store, f"s{idx}", "success", "limit")
        result = plan_next_learning_action(store, task_kind="calculus", task_target="limit")
        assert result["action"] == "REPLAY_STRATEGY"
    finally:
        store.close()


def test_loop_flags_adopted_conflicts_before_new_learning(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        ids = []
        for idx in range(2):
            exp = build_experience(
                action_cycle_id=f"c{idx}",
                outcome="success",
                task_kind="calculus",
                task_target="conflict",
                strategy_id=f"s{idx}",
                strategy_name=f"s{idx}",
                observation="passed",
                evidence_refs=[{"id": f"c{idx}"}],
            )
            ids.append(store.add_experience(exp))
        for statement in ("Prefer A.", "Prefer B."):
            lesson = build_lesson(
                lesson_type="strategy",
                statement=statement,
                scope={"task_kind":"calculus","task_target":"conflict","strategy_id":"shared"},
                supporting_experience_ids=ids,
            )
            store.add_lesson(lesson)
            store.transition_lesson(
                lesson["lesson_id"], "REPRODUCED",
                reason="reproduced",
                evidence=[{"id":"r"}],
            )
            store.transition_lesson(
                lesson["lesson_id"], "VERIFIED",
                reason="independent",
                evidence=[{"id":"i","independence":"independent_route"}],
            )
            store.transition_lesson(
                lesson["lesson_id"], "ADOPTED",
                reason="cross engine",
                evidence=[{"id":"x","independence":"cross_engine"}],
            )
        result = plan_next_learning_action(store, task_kind="calculus", task_target="conflict")
        assert result["action"] == "VERIFY_CONFLICT"
    finally:
        store.close()
