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
