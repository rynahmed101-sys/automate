from pathlib import Path
from subprocess import CompletedProcess
import json

import pytest

from automate.dev.failure_recovery import (
    exact_head_recovery_state,
    quarantine_worker_pr,
    rerun_failed_workflows,
    next_recovery_attempt,
    find_quarantined_worker_handoff,
    build_repair_hold,
)
from automate.dev.publisher import worker_branch_name


def _gh_json(*, conclusion="failure", attempt=1, active=False):
    run = {
        "id": 100,
        "head_sha": "a" * 40,
        "status": "in_progress" if active else "completed",
        "conclusion": None if active else conclusion,
        "run_attempt": attempt,
        "updated_at": "2026-10-08T00:00:00Z",
        "html_url": "https://github.com/example/run/100",
    }
    return CompletedProcess([], 0, json.dumps({"workflow_runs": [run]}), "")


def test_recovery_detects_one_failed_exact_head_run_as_retryable(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(
        "automate.dev.failure_recovery._run",
        lambda args: _gh_json(attempt=1),
    )

    result = exact_head_recovery_state("owner/repo", "a" * 40)
    assert result["state"] == "retryable_failure"
    assert result["retryable"][0]["attempt"] == 1


def test_recovery_stops_retrying_after_second_failed_attempt(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(
        "automate.dev.failure_recovery._run",
        lambda args: _gh_json(attempt=2),
    )

    result = exact_head_recovery_state("owner/repo", "a" * 40)
    assert result["state"] == "repeated_failure"
    assert result["retryable"] == []


def test_recovery_waits_for_active_exact_head_workflow(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(
        "automate.dev.failure_recovery._run",
        lambda args: _gh_json(active=True),
    )

    result = exact_head_recovery_state("owner/repo", "a" * 40)
    assert result["state"] == "pending"
    assert set(result["pending"]) == {"ci.yml", "security.yml"}


def test_recovery_reruns_only_failed_workflow_ids(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return CompletedProcess(args, 0, "", "")

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr("automate.dev.failure_recovery._run", fake_run)

    result = rerun_failed_workflows(
        "owner/repo",
        [{"run_id": 12, "attempt": 1}, {"run_id": 13, "attempt": 1}],
    )
    assert result == {"requested": [12, 13], "errors": []}
    assert all(args[:3] == ["gh", "run", "rerun"] for args in calls)


def test_recovery_quarantine_is_explicit_and_non_promotional(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return CompletedProcess(args, 0, "", "")

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr("automate.dev.failure_recovery._run", fake_run)

    result = quarantine_worker_pr(
        "owner/repo",
        42,
        [{"workflow": "ci.yml", "run_id": 99, "attempt": 2}],
    )
    assert result["state"] == "quarantined"
    assert result["pr_number"] == 42
    assert "--comment" in calls[0]
    assert "not certified or promoted" in calls[0][calls[0].index("--comment") + 1]


def test_recovery_attempts_use_distinct_worker_branches():
    base = "b" * 40
    assert worker_branch_name("stage1b.series_expansions", base) == (
        "feat/stage1b.series_expansions-" + "b" * 12
    )
    assert worker_branch_name("stage1b.series_expansions", base, 2) == (
        "feat/stage1b.series_expansions-" + "b" * 12 + "-repair2"
    )


def test_recovery_worker_request_identity_changes_with_attempt():
    from automate.dev.worker import build_worker_request_id

    kwargs = {
        "repository": "rynahmed101-sys/automate",
        "base_sha_claim": "a" * 40,
        "development_branch": "main",
    }
    first = build_worker_request_id("stage1b.series_expansions", recovery_attempt=None, **kwargs)
    repair = build_worker_request_id("stage1b.series_expansions", recovery_attempt=2, **kwargs)
    assert first != repair
    assert repair.startswith("wrk_")


def _backlog_control():
    return {
        "mode": "BACKLOG",
        "queue": {
            "next_action": {
                "action": "implement",
                "capability_id": "stage1b.series_expansions",
            }
        },
        "mirror_discovery_allowed": False,
    }


def test_control_cycle_requests_retry_for_one_failed_exact_head(monkeypatch):
    import automate.dev.control_cycle as cycle

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(cycle, "resolve_operating_mode", lambda: _backlog_control())
    monkeypatch.setattr(cycle, "find_quarantined_worker_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cycle,
        "_gh_json",
        lambda *_: {"object": {"sha": "a" * 40}},
    )
    monkeypatch.setattr(cycle, "inspect_merged_worker_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cycle,
        "find_worker_handoff",
        lambda *args, **kwargs: {
            "number": 77,
            "head_sha": "b" * 40,
            "request_id": "wrk_test",
        },
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.exact_head_recovery_state",
        lambda *_: {
            "state": "retryable_failure",
            "retryable": [{"run_id": 101, "attempt": 1, "workflow": "ci.yml"}],
            "failures": [{"run_id": 101, "attempt": 1, "workflow": "ci.yml"}],
        },
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.rerun_failed_workflows",
        lambda *_args: {"requested": [101], "errors": []},
    )
    result = cycle.run_control_cycle("owner/repo")
    assert result["status"] == "worker_verification_retry_requested"
    assert result["retry"]["requested"] == [101]


def test_control_cycle_quarantines_repeated_worker_failure_without_transport(monkeypatch):
    import automate.dev.control_cycle as cycle

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(cycle, "resolve_operating_mode", lambda: _backlog_control())
    monkeypatch.setattr(cycle, "_gh_json", lambda *_: {"object": {"sha": "a" * 40}})
    monkeypatch.setattr(cycle, "inspect_merged_worker_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cycle,
        "find_worker_handoff",
        lambda *args, **kwargs: {
            "number": 77,
            "head_sha": "b" * 40,
            "request_id": "wrk_test",
        },
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.exact_head_recovery_state",
        lambda *_: {
            "state": "repeated_failure",
            "failures": [{"run_id": 101, "attempt": 2, "workflow": "ci.yml"}],
        },
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.diagnose_worker_failure",
        lambda *_: {
            "state": "diagnosed",
            "changed_paths": ["automate/backend/x.py"],
            "failure_classes": ["test"],
            "notes": ["fix test"],
        },
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.quarantine_worker_pr",
        lambda *_: {"state": "quarantined", "pr_number": 77},
    )
    result = cycle.run_control_cycle("owner/repo")
    assert result["status"] == "repair_hold"
    assert result["quarantine"]["state"] == "quarantined"
    assert "AUTONOMOUS_RECOVERY" in result["repair_context"][0]
    assert result["repair_hold"]["automatic_rectification_required"] is True
    assert result["repair_hold"]["dispatch_blocked"] is True


def test_recovery_generation_increments_from_repair_branch():
    assert next_recovery_attempt("feat/stage1b.series_expansions-aaaaaaaaaaaa") == 2
    assert next_recovery_attempt("feat/stage1b.series_expansions-aaaaaaaaaaaa-repair2") == 3
    assert next_recovery_attempt("feat/stage1b.series_expansions-aaaaaaaaaaaa-repair9") == 10


def test_repair_hold_builder_is_machine_readable():
    hold = build_repair_hold(
        capability_id="stage1b.series_expansions",
        source_sha="a" * 40,
        recovery_attempt=3,
        reason="repeated failure",
    )
    assert hold["schema_version"] == "automate.repair_hold.v1"
    assert hold["state"] == "REPAIR_HOLD"
    assert hold["automatic_correction_required"] is True
    assert hold["automatic_rectification_required"] is True
    assert hold["recovery_attempt"] == 3
    assert hold["dispatch_blocked"] is True


def test_quarantined_worker_pr_creates_durable_hold_signal(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    closed = {
        "number": 88,
        "headRefName": "feat/stage1b.series_expansions-aaaaaaaaaaaa",
        "headRefOid": "b" * 40,
        "body": "\n".join([
            "AUTONOMOUS RECOVERY: repeated failure",
            "- capability: stage1b.series_expansions",
        ]),
        "mergedAt": None,
        "closedAt": "2026-10-08T00:00:00Z",
        "url": "https://github.com/example/pull/88",
    }
    monkeypatch.setattr(
        "automate.dev.failure_recovery._run",
        lambda args: CompletedProcess(args, 0, json.dumps([closed]), ""),
    )
    result = find_quarantined_worker_handoff(
        "owner/repo", capability_id="stage1b.series_expansions"
    )
    assert result is not None
    assert result["state"] == "REPAIR_HOLD"
    assert result["pr_number"] == 88
    assert result["head_sha"] == "b" * 40


def test_control_cycle_stays_on_durable_repair_hold(monkeypatch):
    import automate.dev.control_cycle as cycle

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(cycle, "resolve_operating_mode", lambda: _backlog_control())
    monkeypatch.setattr(cycle, "_gh_json", lambda *_: {"object": {"sha": "a" * 40}})
    monkeypatch.setattr(cycle, "inspect_merged_worker_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(cycle, "find_worker_handoff", lambda *args, **kwargs: {
        "number": 77,
        "head_sha": "b" * 40,
        "request_id": "wrk_test",
    })
    monkeypatch.setattr(
        "automate.dev.failure_recovery.find_quarantined_worker_handoff",
        lambda *args, **kwargs: {
            "state": "REPAIR_HOLD",
            "pr_number": 88,
            "branch": "feat/stage1b.series_expansions-aaaaaaaaaaaa",
            "head_sha": "b" * 40,
        },
    )
    result = cycle.run_control_cycle("owner/repo")
    assert result["status"] == "repair_hold"
    assert result["dispatch_allowed"] is False
    assert result["repair_hold"]["state"] == "REPAIR_HOLD"
