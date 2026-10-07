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
