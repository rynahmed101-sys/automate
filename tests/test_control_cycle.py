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
