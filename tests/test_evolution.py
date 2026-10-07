from pathlib import Path
import pytest

from automate.dev.evolution import EvolutionPlanError, build_evolution_plan
from automate.dev.learning import build_evolution_proposal


def _proposal(status="ADOPTED"):
    return build_evolution_proposal(
        kind="verifier",
        subject="add independent residual verifier",
        rationale="repeated evidence shows a gap in current checking",
        expected_benefit="more independent verification coverage",
        evidence_refs=[{"id":"verified-evidence"}],
        regression_requirements=["run residual regression corpus"],
        rollback="revert the isolated verifier PR",
        status=status,
    )


def test_evolution_plan_requires_adopted_mutable_proposal():
    proposal = _proposal(status="CANDIDATE")
    with pytest.raises(EvolutionPlanError, match="ADOPTED"):
        build_evolution_plan(
            proposal,
            base_revision="a"*40,
            allowed_path_prefixes=["automate/backend"],
            changes=[{
                "path":"automate/backend/example.py",
                "operation":"create",
                "expected_sha":None,
                "content":"# candidate",
            }],
        )


def test_evolution_plan_is_bounded_and_reversible():
    proposal = _proposal()
    plan = build_evolution_plan(
        proposal,
        base_revision="a"*40,
        allowed_path_prefixes=["automate/backend"],
        changes=[{
            "path":"automate/backend/example.py",
            "operation":"create",
            "expected_sha":None,
            "content":"# candidate",
        }],
    )
    assert plan.to_dict()["apply_mode"] == "proposal_only"
    assert plan.to_dict()["base_revision"] == "a"*40


def test_evolution_plan_rejects_authority_path():
    proposal = _proposal()
    with pytest.raises(EvolutionPlanError, match="authority/security"):
        build_evolution_plan(
            proposal,
            base_revision="a"*40,
            allowed_path_prefixes=["docs"],
            changes=[{
                "path":"docs/PROJECT_PHASE_LEDGER.md",
                "operation":"update",
                "expected_sha":"b"*40,
                "content":"do not mutate",
            }],
        )


def test_evolution_plan_rejects_delete():
    proposal = _proposal()
    with pytest.raises(EvolutionPlanError, match="create/update"):
        build_evolution_plan(
            proposal,
            base_revision="a"*40,
            allowed_path_prefixes=["automate"],
            changes=[{
                "path":"automate/x.py",
                "operation":"delete",
                "expected_sha":"b"*40,
                "content":"",
            }],
        )


def test_evolution_proposal_requires_independent_evidence_and_regressions(tmp_path: Path):
    from automate.dev.learning import LearningStore

    proposal = _proposal(status="CANDIDATE")
    store = LearningStore(tmp_path / "learning.db")
    try:
        store.add_evolution_proposal(proposal)
        store.transition_evolution_proposal(
            proposal["proposal_id"],
            "VERIFIED",
            reason="independent verification",
            evidence=[{"id": "v1", "independence": "independent_route"}],
            regression_results=[{"name": "replay", "status": "passed"}],
        )
        with pytest.raises(Exception, match="independent"):
            store.transition_evolution_proposal(
                proposal["proposal_id"],
                "ADOPTED",
                reason="adopt",
                evidence=[{"id": "same-run"}],
                regression_results=[{"name": "replay", "status": "passed"}],
            )
        adopted = store.transition_evolution_proposal(
            proposal["proposal_id"],
            "ADOPTED",
            reason="cross-engine verification",
            evidence=[{"id": "v2", "independence": "cross_engine"}],
            regression_results=[{"name": "replay", "status": "passed"}],
        )
        assert adopted["status"] == "ADOPTED"
        assert len(adopted["regression_results"]) == 2
    finally:
        store.close()


def test_adopted_system_improvement_lesson_generates_mutable_evolution_candidate(tmp_path: Path):
    from automate.dev.learning import LearningStore, build_experience, build_lesson

    store = LearningStore(tmp_path / "learning.db")
    try:
        exp = build_experience(
            action_cycle_id="system-improvement-1",
            outcome="failure",
            task_kind="autonomous_cycle",
            task_target="worker_validation",
            strategy_id="frontier-default",
            strategy_name="Frontier default",
            observation="worker output repeatedly hit a boundary",
            evidence_refs=[{"id": "run-1"}],
            failure_class="contract_schema_defect",
        )
        eid = store.add_experience(exp)
        lesson = build_lesson(
            lesson_type="system_improvement",
            statement="Strengthen worker validation for recurring contract-boundary failures.",
            scope={
                "task_kind": "autonomous_cycle",
                "target": "automate/dev/worker.py",
                "evolution_kind": "verifier",
            },
            supporting_experience_ids=[eid],
            expected_effect="Reject malformed worker results earlier.",
        )
        store.add_lesson(lesson)
        store.transition_lesson(
            lesson["lesson_id"], "REPRODUCED",
            reason="failure reproduced",
            evidence=[{"id": "reproduction"}],
        )
        store.transition_lesson(
            lesson["lesson_id"], "VERIFIED",
            reason="independent verifier reproduced the boundary",
            evidence=[{"id": "independent", "independence": "independent_route"}],
        )
        store.transition_lesson(
            lesson["lesson_id"], "ADOPTED",
            reason="cross-engine agreement",
            evidence=[{"id": "cross", "independence": "cross_engine"}],
        )
        candidates = store.evolution_candidates_from_adopted_lessons()
        assert len(candidates) == 1
        assert candidates[0]["kind"] == "verifier"
        assert candidates[0]["status"] == "CANDIDATE"
        assert candidates[0]["auto_promotable"] is True
    finally:
        store.close()
