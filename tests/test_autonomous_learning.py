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


def test_learned_strategy_can_override_default_only_after_threshold(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        for index in range(3):
            from automate.dev.learning import build_experience

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
            store.add_experience(experience)

        selected = store.select_strategy(
            task_kind="capability_implementation",
            task_target="stage1b.example",
            minimum_attempts=3,
            minimum_conservative_score=0.1,
        )
        assert selected["strategy_id"] == "strategy-b"
        assert selected["source"] == "learned_experience"
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
