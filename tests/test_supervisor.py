"""Tests for deterministic autonomous supervisor decisions."""

from automate.dev.supervisor import supervisor_snapshot


def test_supervisor_stops_when_live_audit_fails(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.supervisor.summarize_live",
        lambda _: {"repository": "x", "valid": False, "errors": ["bad live state"]},
    )
    result = supervisor_snapshot("rynahmed101-sys/automate")
    assert result["action"] == "stop"
    assert result["can_dispatch"] is False
    assert "bad live state" in result["errors"]


def test_supervisor_reports_current_frontier_without_dispatching(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.supervisor.summarize_live",
        lambda _: {"repository": "x", "valid": True, "errors": []},
    )
    result = supervisor_snapshot(
        "rynahmed101-sys/automate",
        base_sha="0000000000000000000000000000000000000000",
    )
    assert result["action"] == "continue_development"
    assert result["can_dispatch"] is False
    assert result["queue"]["next_action"]["capability_ids"] == ["stage1b.improper_integrals"]
