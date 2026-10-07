from subprocess import CompletedProcess
from unittest.mock import patch

from automate.dev.failure_recovery import (
    exact_head_recovery_state,
    quarantine_worker_pr,
    rerun_failed_workflows,
)
from automate.dev.publisher import worker_branch_name


def _gh_json(workflow, *, conclusion="failure", attempt=1, active=False):
    if active:
        run = {
            "id": 100,
            "head_sha": "a" * 40,
            "status": "in_progress",
            "conclusion": None,
            "run_attempt": attempt,
            "updated_at": "2026-10-08T00:00:00Z",
        }
    else:
        run = {
            "id": 100,
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": conclusion,
            "run_attempt": attempt,
            "updated_at": "2026-10-08T00:00:00Z",
            "html_url": "https://github.com/example/run/100",
        }
    return CompletedProcess(
        [],
        0,
        '{"workflow_runs":[' + __import__("json").dumps(run) + "]}",
        "",
    )


def test_recovery_detects_one_failed_exact_head_run_as_retryable(monkeypatch):
    def fake_run(args):
        workflow = args[2].split("/workflows/")[1].split("/")[0]
        return _gh_json(workflow, conclusion="failure", attempt=1)

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr("automate.dev.failure_recovery._run", fake_run)

    result = exact_head_recovery_state("owner/repo", "a" * 40)
    assert result["state"] == "retryable_failure"
    assert result["retryable"][0]["attempt"] == 1


def test_recovery_stops_retrying_after_second_failed_attempt(monkeypatch):
    def fake_run(args):
        workflow = args[2].split("/workflows/")[1].split("/")[0]
        return _gh_json(workflow, conclusion="failure", attempt=2)

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr("automate.dev.failure_recovery._run", fake_run)

    result = exact_head_recovery_state("owner/repo", "a" * 40)
    assert result["state"] == "repeated_failure"
    assert result["retryable"] == []


def test_recovery_waits_for_active_exact_head_workflow(monkeypatch):
    def fake_run(args):
        workflow = args[2].split("/workflows/")[1].split("/")[0]
        return _gh_json(workflow, active=True)

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr("automate.dev.failure_recovery._run", fake_run)

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
    assert all(args[0:3] == ["gh", "run", "rerun"] for args in calls)


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
