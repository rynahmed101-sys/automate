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


def test_inventory_repository_maps_live_prs_to_capability_metadata(monkeypatch):
    from automate.dev import reconciliation as module

    def api(path):
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "a"*40}}
        if path.endswith("/git/ref/heads/engine"):
            return {"object": {"sha": "b"*40}}
        if path.endswith("/git/commits/" + "a"*40):
            return {"tree": {"sha": "c"*40}}
        if path.endswith("/git/commits/" + "b"*40):
            return {"tree": {"sha": "d"*40}}
        if "/git/trees/" in path:
            return {"sha": path.rsplit("/", 1)[-1].split("?")[0], "tree": []}
        if path.endswith("/pulls?state=all&per_page=100"):
            return [{"number": 133, "state": "open", "merged_at": None, "draft": False, "base": {"sha": "a"*40}, "head": {"sha": "b"*40}, "title": "ODE", "updated_at": None}]
        if path.endswith("/branches?per_page=100"):
            return [{"name": "main"}, {"name": "engine"}]
        if "/actions/runs?branch=main" in path or "/actions/runs?branch=engine" in path:
            return {"workflow_runs": []}
        raise AssertionError(path)

    monkeypatch.setattr(module, "gh_api", api)
    monkeypatch.setattr(module, "load_inventory", lambda: {
        "capabilities": [{
            "id": "stage1c.ode",
            "stage": "1C",
            "implementation_state": "preserved_out_of_order",
            "references": [{"type": "pr", "number": 133, "state": "open"}],
        }],
        "integration_references": [],
    })
    inv = module.inventory_repository("rynahmed101-sys/automate")
    assert inv["observed"]["pull_requests"][0]["capabilities"][0]["capability_id"] == "stage1c.ode"
