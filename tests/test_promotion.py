"""Tests for the evidence-gated promotion state machine."""

from automate.dev.promotion import evaluate_post_merge, evaluate_promotion


def _pr(**overrides):
    body = {
        "number": 7,
        "state": "open",
        "draft": False,
        "review_decision": "",
        "mergeable": True,
        "base": {"ref": "main", "sha": "1" * 40},
        "head": {"ref": "feat/stage1b.series_expansions", "sha": "2" * 40},
    }
    body.update(overrides)
    return body


def _run(sha="2" * 40):
    return {
        "id": 10,
        "status": "completed",
        "conclusion": "success",
        "head_sha": sha,
    }


def test_promotion_requires_current_main_base():
    result = evaluate_promotion(
        _pr(),
        capability_id="stage1b.series_expansions",
        current_main_sha="3" * 40,
        ci_run=_run(),
        security_run=_run(),
    )
    assert result["state"] == "BLOCKED"
    assert result["gates"]["base_is_current"] is False
    assert "reconciliation" in " ".join(result["reasons"])


def test_promotion_requires_security_evidence_on_exact_head():
    result = evaluate_promotion(
        _pr(),
        capability_id="stage1b.series_expansions",
        current_main_sha="1" * 40,
        ci_run=_run(),
        security_run=None,
    )
    assert result["state"] == "BLOCKED"
    assert result["gates"]["development_ci_verified"] is True
    assert result["gates"]["security_audit_verified"] is False


def test_promotion_never_accepts_control_plane_as_capability():
    result = evaluate_promotion(
        _pr(head={"ref": "feat/operating-mode-contract-20261007", "sha": "2" * 40}),
        capability_id=None,
        current_main_sha="1" * 40,
        ci_run=_run(),
        security_run=_run(),
    )
    assert result["state"] == "BLOCKED"
    assert result["gates"]["capability_owned"] is False


def test_promotion_can_be_ready_without_required_review():
    result = evaluate_promotion(
        _pr(),
        capability_id="stage1b.series_expansions",
        current_main_sha="1" * 40,
        ci_run=_run(),
        security_run=_run(),
    )
    assert result["state"] == "READY_TO_MERGE"


def test_post_merge_requires_exact_main_sha_evidence():
    result = evaluate_post_merge(
        capability_id="stage1b.series_expansions",
        merged_main_sha="4" * 40,
        exact_head_ci_run=_run("5" * 40),
        exact_head_security_run=_run("4" * 40),
    )
    assert result["state"] == "VERIFYING_EXACT_MAIN"


def test_post_merge_unlocks_bookkeeping_only_after_exact_main_success():
    result = evaluate_post_merge(
        capability_id="stage1b.series_expansions",
        merged_main_sha="4" * 40,
        exact_head_ci_run=_run("4" * 40),
        exact_head_security_run=_run("4" * 40),
    )
    assert result["state"] == "BOOKKEEPING_READY"
    assert result["canonical_ledger_mutated"] is False


def test_promotion_lifecycle_reports_ready_to_implement_without_open_or_merged_pr():
    from unittest.mock import patch
    from automate.dev.promotion import inspect_capability_lifecycle

    inventory = {
        "capabilities": [{
            "id": "stage1b.series_expansions",
            "implementation_state": "planned",
            "references": [],
        }]
    }
    with patch("automate.dev.promotion.load_inventory", return_value=inventory):
        result = inspect_capability_lifecycle(
            "owner/repo",
            capability_id="stage1b.series_expansions",
            current_main_sha="a" * 40,
        )
    assert result["state"] == "READY_TO_IMPLEMENT"


def test_validated_worker_handoff_can_satisfy_temporary_ownership():
    from automate.dev.promotion import evaluate_promotion

    pr = _pr(
        head={"ref": "feat/stage1b.series_expansions-aaaaaaaaaaaa", "sha": "2" * 40},
    )
    result = evaluate_promotion(
        pr,
        capability_id="stage1b.series_expansions",
        current_main_sha="1" * 40,
        ci_run=_run(),
        security_run=_run(),
    )
    assert result["state"] == "READY_TO_MERGE"
