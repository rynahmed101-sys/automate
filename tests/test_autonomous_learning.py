from pathlib import Path

from automate.dev.autonomous import run_autonomous_cycle
from automate.dev.learning import LearningStore


def test_autonomous_cycle_records_control_plane_outcome(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "automate.dev.autonomous.supervisor_snapshot",
        lambda *_args, **_kwargs: {
            "action": "stop",
            "can_dispatch": False,
            "errors": ["control plane invalid"],
        },
    )

    db = tmp_path / "learning.db"
    result = run_autonomous_cycle(
        "rynahmed101-sys/automate",
        learning_db=db,
    )

    assert result["status"] == "stopped"
    store = LearningStore(db)
    try:
        snapshot = store.snapshot()
        assert snapshot["experience_count"] == 1
        experience = store.get_experience(
            store.db.execute("SELECT id FROM experiences").fetchone()[0]
        )
        assert experience["outcome"] == "unknown"
        assert experience["failure_class"] == "integration_defect"
    finally:
        store.close()


def test_learned_strategy_requires_adopted_lesson_before_override(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        experience_ids = []
        from automate.dev.learning import build_experience, build_lesson

        for index in range(3):
            experience = build_experience(
                action_cycle_id=f"cycle-{index}",
                outcome="success",
                task_kind="capability_implementation",
                task_target="stage1b.example",
                strategy_id="strategy-b",
                strategy_name="Strategy B",
                observation=f"successful run {index}",
                evidence_refs=[{"id": f"e-{index}"}],
                repository="test/repo",
                revision="a" * 40,
                correlation_id=f"cycle-{index}",
                reproducible=True,
            )
            experience_ids.append(store.add_experience(experience))

        before = store.select_strategy(
            task_kind="capability_implementation",
            task_target="stage1b.example",
            minimum_attempts=3,
            minimum_conservative_score=0.1,
        )
        assert before["strategy_id"] == "frontier-default"

        lesson = build_lesson(
            lesson_type="strategy",
            statement="Strategy B generalized across reproduced examples.",
            scope={
                "task_kind": "capability_implementation",
                "task_target": "stage1b.example",
                "strategy_id": "strategy-b",
            },
            supporting_experience_ids=experience_ids,
        )
        store.add_lesson(lesson)
        store.transition_lesson(
            lesson["lesson_id"],
            "REPRODUCED",
            reason="reproduction",
            evidence=[{"id": "reproduction"}],
        )
        store.transition_lesson(
            lesson["lesson_id"],
            "REPRODUCED",
            reason="independent route reproduced the successful strategy",
            evidence=[{"id": "reproduction"}],
        )
        store.transition_lesson(
            lesson["lesson_id"],
            "VERIFIED",
            reason="independent route reproduced the successful strategy",
            evidence=[{"id": "independent-1", "independence": "independent_route"}],
        )
        store.transition_lesson(
            lesson["lesson_id"],
            "ADOPTED",
            reason="cross-check passed",
            evidence=[{"id": "cross-check-1", "independence": "cross_engine"}],
        )

        selected = store.select_strategy(
            task_kind="capability_implementation",
            task_target="stage1b.example",
            minimum_attempts=3,
            minimum_conservative_score=0.1,
        )
        assert selected["strategy_id"] == "strategy-b"
        assert selected["source"] == "adopted_lesson"
    finally:
        store.close()


def test_evolution_proposal_round_trips_through_learning_store(tmp_path: Path):
    from automate.dev.learning import build_evolution_proposal

    proposal = build_evolution_proposal(
        kind="verifier",
        subject="add independent residual checker",
        rationale="repeated evidence shows symbolic-only checking is weak here",
        expected_benefit="broader independent verification coverage",
        evidence_refs=[{"id": "evidence-1"}],
        regression_requirements=["run residual corpus"],
        rollback="revert the isolated verifier commit",
    )
    store = LearningStore(tmp_path / "learning.db")
    try:
        assert store.add_evolution_proposal(proposal) == proposal["proposal_id"]
        assert store.get_evolution_proposal(proposal["proposal_id"]) == proposal
    finally:
        store.close()


def test_candidate_lessons_include_regression_obligations(tmp_path: Path):
    from automate.dev.learning import build_experience

    store = LearningStore(tmp_path / "learning.db")
    try:
        experience = build_experience(
            action_cycle_id="cycle-regression",
            outcome="failure",
            task_kind="calculus",
            task_target="stage1b.example",
            strategy_id="strategy-b",
            strategy_name="Strategy B",
            observation="reproduced boundary failure",
            evidence_refs=[{"id": "failure-run"}],
            failure_class="missing_assumption",
            repository="test/repo",
            revision="a" * 40,
            correlation_id="cycle-regression",
            reproducible=True,
        )
        store.add_experience(experience)
        candidates = store.regression_candidates()
        assert len(candidates) == 1
        assert candidates[0]["experience_id"] == experience["experience_id"]
        assert "regression_obligation" in candidates[0]
    finally:
        store.close()


def test_adopted_lesson_guidance_is_returned_for_worker_selection(tmp_path: Path):
    from automate.dev.learning import build_experience, build_lesson

    store = LearningStore(tmp_path / "learning.db")
    try:
        ids = []
        for index in range(3):
            exp = build_experience(
                action_cycle_id=f"guided-{index}",
                outcome="success",
                task_kind="capability_implementation",
                task_target="stage1b.example",
                strategy_id="strategy-guided",
                strategy_name="Guided strategy",
                observation="successful guided execution",
                evidence_refs=[{"id": f"e-{index}"}],
                repository="test/repo",
                revision="a" * 40,
                correlation_id=f"guided-{index}",
                reproducible=True,
            )
            ids.append(store.add_experience(exp))

        lesson = build_lesson(
            lesson_type="strategy",
            statement="Preserve explicit endpoint assumptions before convergence checks.",
            scope={
                "task_kind": "capability_implementation",
                "task_target": "stage1b.example",
                "strategy_id": "strategy-guided",
            },
            supporting_experience_ids=ids,
            preconditions=["domain and orientation are explicit"],
        )
        store.add_lesson(lesson)
        store.transition_lesson(
            lesson["lesson_id"], "VERIFIED",
            reason="independent reproduction",
            evidence=[{"id": "independent", "independence": "independent_route"}],
        )
        store.transition_lesson(
            lesson["lesson_id"], "ADOPTED",
            reason="cross-engine agreement",
            evidence=[{"id": "cross-engine", "independence": "cross_engine"}],
        )

        selected = store.select_strategy(
            task_kind="capability_implementation",
            task_target="stage1b.example",
            minimum_attempts=3,
            minimum_conservative_score=0.1,
        )
        assert selected["adopted_lessons"][0]["lesson_id"] == lesson["lesson_id"]
        assert "endpoint assumptions" in selected["adopted_lessons"][0]["statement"]
        assert selected["adopted_lessons"][0]["preconditions"] == [
            "domain and orientation are explicit"
        ]
    finally:
        store.close()
