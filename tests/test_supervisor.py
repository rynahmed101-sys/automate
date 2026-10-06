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


def test_supervisor_can_dispatch_current_frontier(monkeypatch):
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
    assert "stage1b.improper_integrals" in result["capability_ids"]
    assert (
        result["worker_packet"]["packet"]["repository"]["base_sha_claim"]
        == "0000000000000000000000000000000000000000"
    )
