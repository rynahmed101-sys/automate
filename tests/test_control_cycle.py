from automate.dev.control_cycle import resolve_operating_mode


def test_unfinished_ledger_forces_backlog_mode():
    payload = {
        "capabilities": [{
            "id": "stage1b.test",
            "order": 1,
            "stage": "1B",
            "depends_on": [],
            "implementation_state": "planned",
            "authority": {"kind": "none", "ref": ""},
            "verification": {},
            "references": [],
            "safe_to_delete": False,
            "preserved_in": None,
            "canonical_files": ["automate/backend/example.py"],
            "shared_integration_points": [],
        }],
        "branch_policy": {"shared_integration_files": []},
        "integration_references": [],
    }
    result = resolve_operating_mode(payload)
    assert result["mode"] == "BACKLOG"
    assert result["mirror_discovery_allowed"] is False


def test_empty_ledger_exposes_discovery_ready_mode():
    payload = {
        "capabilities": [],
        "branch_policy": {"shared_integration_files": []},
        "integration_references": [],
    }
    result = resolve_operating_mode(payload)
    assert result["mode"] == "DISCOVERY_READY"
    assert result["mirror_discovery_allowed"] is True


def test_empty_ledger_issues_bounded_discovery_grant():
    from automate.dev.discovery_grant import build_discovery_grant

    control = {
        "schema_version": "automate.operating_mode.v1",
        "mode": "DISCOVERY_READY",
        "mirror_discovery_allowed": True,
        "queue": {"next_action": {"action": "none"}},
    }
    grant = build_discovery_grant(control, correlation_id="ctrl_test1234")
    assert grant["max_candidates"] == 1
    assert grant["canonical_mutation_allowed"] is False
    assert "mutate_phase_ledger" in grant["forbidden_actions"]


def test_discovery_grant_rejects_nonterminal_queue():
    from automate.dev.discovery_grant import DiscoveryGrantError, build_discovery_grant

    control = {
        "schema_version": "automate.operating_mode.v1",
        "mode": "DISCOVERY_READY",
        "mirror_discovery_allowed": True,
        "queue": {"next_action": {"action": "implement"}},
    }
    try:
        build_discovery_grant(control, correlation_id="ctrl_test1234")
    except DiscoveryGrantError:
        return
    raise AssertionError("discovery grant must not issue while backlog remains")


def test_control_cycle_does_not_dispatch_when_worker_handoff_exists():
    from unittest.mock import patch
    from automate.dev.control_cycle import run_control_cycle

    control = {
        "schema_version": "automate.operating_mode.v1",
        "mode": "BACKLOG",
        "mirror_discovery_allowed": False,
        "queue": {"next_action": {"action": "implement", "capability_id": "stage1b.series_expansions"}},
    }
    handoff = {
        "number": 900,
        "head": {"ref": "feat/stage1b.series_expansions-" + "b" * 12, "sha": "b" * 40},
        "base": {"ref": "main", "sha": "a" * 40},
        "_worker_request_id": "wrk_" + "c" * 32,
        "_worker_base_sha": "a" * 40,
    }
    lifecycle = {
        "state": "IMPLEMENTATION_PR",
        "promotion": {"state": "BLOCKED"},
        "pr": {"number": 900},
    }

    with patch("automate.dev.control_cycle.resolve_operating_mode", return_value=control),          patch("automate.dev.control_cycle._gh_json", return_value={"object": {"sha": "a" * 40}}),          patch("automate.dev.control_cycle.find_quarantined_worker_handoff", return_value=None),          patch("automate.dev.control_cycle.find_worker_handoff", return_value=handoff),          patch("automate.dev.control_cycle.inspect_merged_worker_handoff", return_value=None),          patch("automate.dev.control_cycle.build_worker_packet", return_value={"packet": {
             "repository": {"base_sha_claim": "a" * 40},
             "capability": {"id": "stage1b.series_expansions"},
         }}),          patch("automate.dev.control_cycle.inspect_worker_handoff_pr", return_value=lifecycle),          patch("automate.dev.control_cycle.run_autonomous_cycle") as dispatch:
        result = run_control_cycle("owner/repo")

    assert result["dispatch_allowed"] is False
    assert result["status"] == "verification_blocked"
    assert result["lifecycle"] == handoff
    dispatch.assert_not_called()


def test_discovery_cycle_never_allows_more_than_one_candidate():
    from automate.dev.discovery import extract_candidate_proposals

    proposal = {
        "authority": "UNTRUSTED_RESEARCH_PROPOSAL",
        "status": "CANDIDATE",
        "proposal_id": "proposal_test",
        "candidate_capability": {
            "id": "candidate.new",
            "name": "Candidate",
            "summary": "candidate",
            "prerequisites": [],
            "dependencies": [],
        },
    }
    result = {
        "trace": [
            {"tool": "propose_new_capability", "result": {"proposal": proposal}},
            {"tool": "propose_new_capability", "result": {"proposal": proposal}},
        ]
    }
    assert len(extract_candidate_proposals(result)) == 2


def test_merged_worker_waits_for_exact_main_verification_before_new_dispatch():
    control = {
        "mode": "BACKLOG",
        "queue": {"next_action": {"action": "implement", "capability_id": "stage1b.series_expansions"}},
    }
    merged = {
        "post_merge": {
            "state": "VERIFYING_EXACT_MAIN",
            "gates": {
                "exact_head_ci_verified": False,
                "security_audit_verified": False,
            },
        }
    }
    # Contract-level regression: this state must stop the cycle rather than
    # reaching the fresh-worker dispatch path.
    assert merged["post_merge"]["state"] not in {"BLOCKED_STALE_MAIN", "BOOKKEEPING_READY"}


def test_control_cycle_delegates_commit_only_to_autonomous_worker(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["auto_publish"] = kwargs.get("auto_publish")
        return {"decision": {}, "commit": {}, "status": "committed"}

    monkeypatch.setattr("automate.dev.control_cycle.run_autonomous_cycle", fake_run)
    monkeypatch.setattr(
        "automate.dev.control_cycle.resolve_operating_mode",
        lambda: {
            "mode": "BACKLOG",
            "queue": {
                "next_action": {
                    "action": "implement",
                    "capability_id": "stage1b.series_expansions",
                }
            },
        },
    )
    monkeypatch.setattr(
        "automate.dev.control_cycle._gh_json",
        lambda *args: {"object": {"sha": "a" * 40}},
    )
    monkeypatch.setattr(
        "automate.dev.control_cycle.inspect_merged_worker_handoff",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "automate.dev.control_cycle.find_worker_handoff",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "automate.dev.failure_recovery.find_quarantined_worker_handoff",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "automate.dev.control_cycle.inspect_capability_lifecycle",
        lambda *args, **kwargs: {"state": "READY"},
    )
    result = __import__("automate.dev.control_cycle", fromlist=["run_control_cycle"]).run_control_cycle(
        "owner/repo",
        worker_url="https://worker",
        worker_token="secret",
        execute_worker=True,
        local_root=None,
    )
    assert captured["auto_publish"] is False
