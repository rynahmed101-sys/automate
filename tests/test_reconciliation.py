from automate.dev.reconciliation import build_reconciliation_plan, classify_pull_request

def test_stale_historical_pr_is_candidate_source_not_authority():
    result = classify_pull_request(
        {"number": 89, "state": "closed", "merged": False, "base_sha": "a"*40},
        target_revision="b"*40,
        earliest_stage="1B",
        capability_stage="3A",
    )
    assert result["status"] == "candidate_source"
    assert {f["kind"] for f in result["findings"]} == {"stale_base", "closed_unmerged", "later_stage"}
    assert result["preserve_unique_work_until_compared"] is True

def test_plan_fails_closed_when_authoritative_evidence_is_missing():
    inventory = {
        "observed": {
            "main_sha": "a"*40,
            "pull_requests": [],
            "main_ci": {
                "exact_head_ci_verified": False,
                "exact_head_security_verified": False,
            },
        }
    }
    plan = build_reconciliation_plan(
        inventory,
        earliest_stage="1B",
        target_repository="rynahmed101-sys/automate",
    )
    assert len(plan["evidence_gaps"]) == 2
    assert "blind merge of stale historical PRs" in plan["unsafe_actions"]
    assert plan["plan_fingerprint"]
