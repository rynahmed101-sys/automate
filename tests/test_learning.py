from pathlib import Path

import pytest

from automate.dev.learning import (
    LearningError,
    LearningStore,
    admission_decision,
    build_evolution_proposal,
    build_experience,
    build_lesson,
    validate_experience,
    validate_lesson,
)


def _experience(store: LearningStore, *, outcome: str, strategy_id: str, target: str = "integral") -> str:
    exp = build_experience(
        action_cycle_id=f"cycle-{outcome}-{strategy_id}-{target}",
        outcome=outcome,
        task_kind="calculus",
        task_target=target,
        strategy_id=strategy_id,
        strategy_name=strategy_id,
        observation=f"observed {outcome}",
        evidence_refs=[{"id": f"evidence-{outcome}-{strategy_id}", "kind": "test"}],
        failure_class="missing_assumption" if outcome == "failure" else None,
        repository="test/repo",
        revision="a" * 40,
        correlation_id="corr-1",
        reproducible=outcome != "unknown",
    )
    return store.add_experience(exp)


def test_experience_ids_are_deterministic_and_schema_valid(tmp_path: Path):
    first = build_experience(
        action_cycle_id="cycle-1",
        outcome="failure",
        task_kind="calculus",
        task_target="improper_integral",
        strategy_id="endpoint-aware",
        strategy_name="Endpoint aware",
        observation="upper tail orientation was omitted",
        evidence_refs=[{"id": "run-1"}],
    )
    second = build_experience(
        action_cycle_id="cycle-1",
        outcome="failure",
        task_kind="calculus",
        task_target="improper_integral",
        strategy_id="endpoint-aware",
        strategy_name="Endpoint aware",
        observation="upper tail orientation was omitted",
        evidence_refs=[{"id": "run-1"}],
    )
    assert first["experience_id"] == second["experience_id"]
    assert validate_experience(first) == []


def test_lesson_requires_existing_experiences(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    exp_id = _experience(store, outcome="failure", strategy_id="s1")
    lesson = build_lesson(
        lesson_type="failure",
        statement="Repeated failures share a missing-assumption pattern.",
        scope={"task_kind": "calculus"},
        supporting_experience_ids=[exp_id],
        expected_effect="Investigate assumptions before retrying.",
    )
    assert validate_lesson(lesson) == []
    assert store.add_lesson(lesson) == lesson["lesson_id"]
    with pytest.raises(LearningError):
        store.add_lesson(build_lesson(
            lesson_type="failure",
            statement="bad",
            scope={},
            supporting_experience_ids=["exp_" + "0" * 32],
        ))
    store.close()


def test_lesson_promotion_requires_independent_evidence(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    exp_id = _experience(store, outcome="failure", strategy_id="s1")
    lesson = build_lesson(
        lesson_type="strategy",
        statement="Use endpoint-aware decomposition before convergence evaluation.",
        scope={"task_kind": "calculus", "task_target": "integral"},
        supporting_experience_ids=[exp_id],
    )
    store.add_lesson(lesson)
    with pytest.raises(LearningError):
        store.transition_lesson(
            lesson["lesson_id"],
            "VERIFIED",
            reason="verified",
            evidence=[{"id": "mirror-1"}],
        )
    verified = store.transition_lesson(
        lesson["lesson_id"],
        "VERIFIED",
        reason="independent route reproduced the failure boundary",
        evidence=[{"id": "mirror-1", "independence": "independent_route"}],
    )
    assert verified["status"] == "VERIFIED"
    with pytest.raises(LearningError):
        store.transition_lesson(
            lesson["lesson_id"],
            "ADOPTED",
            reason="adopt",
            evidence=[{"id": "same-run"}],
        )
    adopted = store.transition_lesson(
        lesson["lesson_id"],
        "ADOPTED",
        reason="adopt after cross-check",
        evidence=[{"id": "cross-check-1", "independence": "cross_engine"}],
    )
    assert adopted["status"] == "ADOPTED"
    store.close()


def test_strategy_recommendation_is_conservative(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    for outcome in ("success", "success", "failure"):
        _experience(store, outcome=outcome, strategy_id="a")
    for outcome in ("success", "failure", "failure", "failure"):
        _experience(store, outcome=outcome, strategy_id="b")
    recs = store.strategy_recommendations(task_kind="calculus", task_target="integral")
    assert [r.strategy_id for r in recs][0] == "a"
    assert recs[0].conservative_score < 1.0
    store.close()


def test_failure_candidates_require_repetition(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    _experience(store, outcome="failure", strategy_id="s1", target="integral")
    _experience(store, outcome="failure", strategy_id="s2", target="integral")
    candidates = store.failure_lesson_candidates(min_repetitions=2)
    assert len(candidates) == 1
    assert candidates[0]["status"] == "CANDIDATE"
    assert len(candidates[0]["supporting_experience_ids"]) == 2
    store.close()


def test_constitutional_evolution_cannot_be_auto_promoted():
    proposal = build_evolution_proposal(
        kind="governance",
        subject="change epistemic kernel",
        rationale="experiment suggested a change",
        expected_benefit="broader exploration",
        evidence_refs=[{"id": "e1"}],
        regression_requirements=["run full regression corpus"],
        rollback="revert immutable release",
        constitutional=True,
    )
    decision = admission_decision(
        proposal,
        verified_evidence_count=4,
        regression_results=[{"name": "full-suite", "status": "passed"}],
    )
    assert decision["admit"] is False
    assert decision["status"] == "CONSTITUTIONAL_REVIEW_REQUIRED"


def test_strategy_replay_comparison_is_fail_closed_when_samples_are_sparse(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        _experience(store, outcome="success", strategy_id="baseline", target="replay")
        _experience(store, outcome="success", strategy_id="candidate", target="replay")
        result = store.evaluate_strategy_change(
            task_kind="calculus",
            task_target="replay",
            baseline_strategy_id="baseline",
            candidate_strategy_id="candidate",
            minimum_samples=2,
        )
        assert result["status"] == "INSUFFICIENT_SAMPLES"
    finally:
        store.close()


def test_strategy_replay_comparison_does_not_claim_causality(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        for idx, outcome in enumerate(("success", "failure", "success", "success", "failure")):
            exp = build_experience(
                action_cycle_id=f"baseline-{idx}",
                outcome=outcome,
                task_kind="calculus",
                task_target="replay",
                strategy_id="baseline",
                strategy_name="baseline",
                observation=outcome,
                evidence_refs=[{"id": f"b-{idx}"}],
            )
            store.add_experience(exp)
        for idx, outcome in enumerate(("success", "success", "success", "success", "failure")):
            exp = build_experience(
                action_cycle_id=f"candidate-{idx}",
                outcome=outcome,
                task_kind="calculus",
                task_target="replay",
                strategy_id="candidate",
                strategy_name="candidate",
                observation=outcome,
                evidence_refs=[{"id": f"c-{idx}"}],
            )
            store.add_experience(exp)
        result = store.evaluate_strategy_change(
            task_kind="calculus",
            task_target="replay",
            baseline_strategy_id="baseline",
            candidate_strategy_id="candidate",
            minimum_samples=5,
        )
        assert result["status"] == "candidate_better"
        assert result["causal_claim"] is False
        assert "prospective" in result["next_step"]
    finally:
        store.close()


def test_adopted_lesson_conflicts_are_flagged_without_auto_resolution(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        ids = []
        for idx in range(2):
            ids.append(_experience(store, outcome="success", strategy_id=f"s{idx}", target="conflict"))
        for statement in (
            "Use strategy A for this task.",
            "Use strategy B for this task.",
        ):
            lesson = build_lesson(
                lesson_type="strategy",
                statement=statement,
                scope={
                    "task_kind": "calculus",
                    "task_target": "conflict",
                    "strategy_id": "shared-scope",
                },
                supporting_experience_ids=ids,
            )
            store.add_lesson(lesson)
            store.transition_lesson(
                lesson["lesson_id"], "VERIFIED",
                reason="independent review",
                evidence=[{"id": "independent", "independence": "independent_route"}],
            )
            store.transition_lesson(
                lesson["lesson_id"], "ADOPTED",
                reason="cross-engine review",
                evidence=[{"id": "cross", "independence": "cross_engine"}],
            )
        conflicts = store.lesson_conflicts(lesson_type="strategy")
        assert len(conflicts) == 1
        assert conflicts[0]["requires_verification"] is True
        assert len(conflicts[0]["lesson_ids"]) == 2
    finally:
        store.close()
