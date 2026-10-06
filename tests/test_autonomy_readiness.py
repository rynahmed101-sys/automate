"""Tests for autonomy readiness policy."""

from automate.dev.readiness import evaluate_readiness, REQUIRED_GATES


def test_readiness_is_fail_closed():
    result = evaluate_readiness({})
    assert result["ready"] is False
    assert result["worker_mode"] == "off"
    assert set(result["blocking_gates"]) == set(REQUIRED_GATES)


def test_readiness_requires_every_gate():
    evidence = {gate: True for gate in REQUIRED_GATES}
    evidence["exact_head_authority_current"] = False
    result = evaluate_readiness(evidence)
    assert result["ready"] is False
    assert result["worker_mode"] == "off"
    assert result["blocking_gates"] == ["exact_head_authority_current"]


def test_readiness_turns_on_only_with_complete_evidence():
    evidence = {gate: True for gate in REQUIRED_GATES}
    result = evaluate_readiness(evidence)
    assert result["ready"] is True
    assert result["worker_mode"] == "enabled"
