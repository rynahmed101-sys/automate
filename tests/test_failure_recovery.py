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


def test_recovery_worker_request_identity_changes_with_attempt(monkeypatch):
    from automate.dev.worker import build_worker_packet

    monkeypatch.setattr(
        "automate.dev.worker.load_inventory",
        lambda: {
            "capabilities": [{
                "id": "stage1b.series_expansions",
                "implementation_state": "planned",
                "depends_on": [],
                "canonical_files": ["automate/backend/series_expansions.py", "tests/test_series_expansions.py"],
                "shared_integration_points": [],
                "stage": "1B",
                "name": "Series expansions",
                "references": [],
                "task": {"source": "github_issue", "ref": "141", "summary": "series", "requirements": []},
            }],
            "branch_policy": {
                "shared_integration_files": [],
                "capability_branch_prefix": "feat/",
            },
        },
    )
    monkeypatch.setattr(
        "automate.dev.worker.get_capability",
        lambda _: {
            "id": "stage1b.series_expansions",
            "implementation_state": "planned",
            "depends_on": [],
            "canonical_files": ["automate/backend/series_expansions.py", "tests/test_series_expansions.py"],
            "shared_integration_points": [],
            "stage": "1B",
            "name": "Series expansions",
            "references": [],
            "task": {"source": "github_issue", "ref": "141", "summary": "series", "requirements": []},
        },
    )
    monkeypatch.setattr(
        "automate.dev.worker.ROOT",
        __import__("pathlib").Path("."),
    )
    base = "a" * 40
    context_files = [
        {
            "path": "automate/backend/series_expansions.py",
            "sha": "1" * 40,
            "content": "def series_expansions(): pass",
        },
        {
            "path": "tests/test_series_expansions.py",
            "sha": "2" * 40,
            "content": "def test_series_expansions(): pass",
        },
    ]
    first = build_worker_packet(
        "stage1b.series_expansions",
        base_sha_claim=base,
        context_files=context_files,
    )
    repair = build_worker_packet(
        "stage1b.series_expansions",
        base_sha_claim=base,
        context_files=context_files,
        recovery_attempt=2,
    )
    assert first["packet"]["request_id"] != repair["packet"]["request_id"]
    assert "AUTONOMOUS_RECOVERY_ATTEMPT: 2" in repair["packet"]["context"]["notes"]


def _backlog_control():
    return {
        "mode": "BACKLOG",
        "queue": {"next_action": {"action": "implement", "capability_id": "stage1b.series_expansions"}},
        "mirror_discovery_allowed": False,
    }


def test_control_cycle_requests_retry_for_one_failed_exact_head(monkeypatch):
    import automate.dev.control_cycle as cycle

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(cycle, "resolve_operating_mode", lambda: _backlog_control())
    monkeypatch.setattr(
        cycle,
        "_gh_json",
        lambda *_: {"object": {"sha": "a" * 40}},
    )
    monkeypatch.setattr(
        cycle,
        "inspect_merged_worker_handoff",
        lambda *args, **kwargs: None,
    )
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
        lambda *_: {"state": "diagnosed", "changed_paths": ["automate/backend/x.py"], "failure_classes": ["test"], "notes": ["fix test"]},
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.quarantine_worker_pr",
        lambda *_: {"state": "quarantined", "pr_number": 77},
    )
    result = cycle.run_control_cycle("owner/repo")
    assert result["status"] == "worker_quarantined_repair_ready"
    assert result["quarantine"]["state"] == "quarantined"
    assert "AUTONOMOUS_RECOVERY" in result["repair_context"][0]
