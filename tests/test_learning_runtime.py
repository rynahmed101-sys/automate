from pathlib import Path

from automate.dev.learning import LearningStore
from automate.dev.learning_runtime import (
    build_learning_handoff,
    record_cycle_experience,
    select_learning_strategy,
)


def test_learning_runtime_records_experience_and_candidate_lesson(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    for index in range(3):
        result = record_cycle_experience(
            store,
            action_cycle_id=f"cycle_{index:08d}",
            task_kind="capability_implementation",
            task_target="stage1b.series_expansions",
            strategy_id="frontier-default",
            outcome="success",
            observation="bounded worker path completed successfully",
            revision="a" * 40,
        )
    assert result["experience_id"].startswith("exp_")
    assert result["candidate_lessons_recorded"]
    assert store.list_adopted_lessons(lesson_type="strategy") == []

    selected = select_learning_strategy(
        store,
        task_kind="capability_implementation",
        task_target="stage1b.series_expansions",
    )
    assert selected["strategy_id"] == "frontier-default"
    assert selected["source"] == "default"
    store.close()


def test_learning_runtime_adoption_is_required_before_strategy_change(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    for index in range(10):
        record_cycle_experience(
            store,
            action_cycle_id=f"cycle_{index:08d}",
            task_kind="capability_implementation",
            task_target="stage1b.series_expansions",
            strategy_id="learned-strategy",
            outcome="success",
            observation="learned path completed successfully",
            revision="b" * 40,
        )

    candidates = store.success_lesson_candidates(min_repetitions=3)
    assert candidates
    lesson_id = store.add_lesson(candidates[0])

    selected_before = select_learning_strategy(
        store,
        task_kind="capability_implementation",
        task_target="stage1b.series_expansions",
    )
    assert selected_before["strategy_id"] == "frontier-default"

    store.transition_lesson(
        lesson_id,
        "REPRODUCED",
        reason="independent reproduction recorded",
        evidence=[{"id": "repro_1", "independence": "independent"}],
    )
    store.transition_lesson(
        lesson_id,
        "VERIFIED",
        reason="cross-check passed",
        evidence=[{"id": "verify_1", "independence": "independent"}],
    )
    store.transition_lesson(
        lesson_id,
        "ADOPTED",
        reason="adoption threshold satisfied",
        evidence=[{"id": "adopt_1", "independence": "independent"}],
    )
    selected_after = select_learning_strategy(
        store,
        task_kind="capability_implementation",
        task_target="stage1b.series_expansions",
    )
    assert selected_after["strategy_id"] == "learned-strategy"
    assert selected_after["source"] == "adopted_lesson"
    store.close()


def test_learning_handoff_is_explicitly_untrusted():
    payload = build_learning_handoff(
        {"experience_id": "exp_" + "a" * 32},
        artifact_type="learning_experience",
        request_id="learn_" + "b" * 32,
        correlation_id="cycle_" + "c" * 24,
        source_revision="d" * 40,
    )
    assert payload["authority"] == "UNTRUSTED_LEARNING_EVIDENCE"
    assert payload["schema_version"] == "automate.learning_handoff.v1"
    assert payload["source_revision"] == "d" * 40
