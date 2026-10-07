from pathlib import Path

import pytest

from automate.dev.evolution import build_evolution_plan
from automate.dev.evolution_executor import EvolutionExecutionError, execute_evolution_plan
from automate.dev.learning import build_evolution_proposal


def _plan():
    proposal = build_evolution_proposal(
        kind="strategy",
        subject="improve strategy",
        rationale="repeated verified weakness",
        expected_benefit="better decisions",
        evidence_refs=[{"id": "verified"}],
        regression_requirements=["replay failure corpus"],
        rollback="revert the PR",
        status="ADOPTED",
    )
    return build_evolution_plan(
        proposal,
        base_revision="a" * 40,
        allowed_path_prefixes=["automate/dev"],
        changes=[{
            "path": "automate/dev/example.py",
            "operation": "create",
            "expected_sha": None,
            "content": "VALUE = 1\n",
        }],
    ).to_dict()


def test_executor_requires_explicit_enable(monkeypatch):
    monkeypatch.delenv("AUTOMATE_SELF_EVOLUTION_ENABLED", raising=False)
    with pytest.raises(EvolutionExecutionError, match="disabled"):
        execute_evolution_plan(_plan(), token="secret")


def test_executor_refuses_stale_plan_before_changes(monkeypatch):
    monkeypatch.setenv("AUTOMATE_SELF_EVOLUTION_ENABLED", "1")
    monkeypatch.setattr(
        "automate.dev.evolution_executor._remote_main_sha",
        lambda *_args, **_kwargs: "b" * 40,
    )
    with pytest.raises(EvolutionExecutionError, match="stale"):
        execute_evolution_plan(_plan(), token="secret")


def test_executor_rejects_path_traversal_at_execution_boundary(monkeypatch):
    monkeypatch.setenv("AUTOMATE_SELF_EVOLUTION_ENABLED", "1")
    monkeypatch.setattr(
        "automate.dev.evolution_executor._remote_main_sha",
        lambda *_args, **_kwargs: "a" * 40,
    )
    plan = _plan()
    plan["changes"][0]["path"] = "automate/dev/../secrets.py"
    with pytest.raises(EvolutionExecutionError, match="safe relative path"):
        execute_evolution_plan(plan, token="secret")


def test_executor_rejects_absolute_evolution_path(monkeypatch):
    monkeypatch.setenv("AUTOMATE_SELF_EVOLUTION_ENABLED", "1")
    monkeypatch.setattr(
        "automate.dev.evolution_executor._remote_main_sha",
        lambda *_args, **_kwargs: "a" * 40,
    )
    plan = _plan()
    plan["changes"][0]["path"] = "/automate/dev/example.py"
    with pytest.raises(EvolutionExecutionError, match="safe relative path"):
        execute_evolution_plan(plan, token="secret")
