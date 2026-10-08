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
    from pathlib import Path

    root = Path(__import__("tempfile").mkdtemp())
    (root / "automate/backend").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "automate/backend/series_expansions.py").write_text(
        "def series_expansions(): pass",
        encoding="utf-8",
    )
    (root / "tests/test_series_expansions.py").write_text(
        "def test_series_expansions(): pass",
        encoding="utf-8",
    )
    monkeypatch.setattr("automate.dev.worker.ROOT", root)
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