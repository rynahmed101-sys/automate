from unittest.mock import patch

from automate.dev.failure_recovery import exact_head_recovery_state
from automate.dev.publisher import worker_branch_name


def test_repeated_failure_is_quarantined():
    runs = [
        [{"databaseId": 101, "headSha": "a" * 40, "status": "completed", "conclusion": "failure", "attempt": 2}],
        [{"databaseId": 201, "headSha": "a" * 40, "status": "completed", "conclusion": "success", "attempt": 1}],
    ]
    with patch("automate.dev.failure_recovery._workflow_runs", side_effect=runs):
        result = exact_head_recovery_state("test/automate", "a" * 40)
    assert result["state"] == "repeated_failure"


def test_single_failure_is_retryable():
    runs = [
        [{"databaseId": 101, "headSha": "b" * 40, "status": "completed", "conclusion": "failure", "attempt": 1}],
        [{"databaseId": 201, "headSha": "b" * 40, "status": "completed", "conclusion": "success", "attempt": 1}],
    ]
    with patch("automate.dev.failure_recovery._workflow_runs", side_effect=runs):
        result = exact_head_recovery_state("test/automate", "b" * 40)
    assert result["state"] == "retryable_failure"


def test_repair_branch_is_distinct():
    sha = "c" * 40
    assert worker_branch_name("stage1b.series_expansions", sha, 2).endswith("-repair2")


def test_recovery_contracts_exist_and_hold_is_fail_closed():
    from automate.dev.failure_recovery import build_repair_hold, next_recovery_attempt, diagnose_worker_failure

    assert next_recovery_attempt("feat/stage1b.x-abc-repair2") == 3
    assert next_recovery_attempt("feat/stage1b.x-abc") == 2
    hold = build_repair_hold(
        capability_id="stage1b.x",
        source_sha="a" * 40,
        recovery_attempt=2,
        reason="repeated exact-head failure",
    )
    assert hold["state"] == "REPAIR_HOLD"
    assert hold["dispatch_blocked"] is True
    diagnosis = diagnose_worker_failure("owner/repo", 1, [{
        "workflow": "Automate CI", "conclusion": "failure", "attempt": 2, "run_id": 1,
    }])
    assert diagnosis["authority"] == "EVIDENCE_ONLY"
