"""Tests for the machine-readable development control plane."""
import json

from click.testing import CliRunner

from automate.cli import main
from automate.dev.inventory import load_inventory, validate_inventory


def test_inventory_is_valid():
    data = load_inventory()
    assert validate_inventory(data) == []


def test_inventory_ids_and_orders_are_unique():
    data = load_inventory()
    ids = [x["id"] for x in data["capabilities"]]
    orders = [x["order"] for x in data["capabilities"]]
    assert len(ids) == len(set(ids))
    assert len(orders) == len(set(orders))


def test_active_direct_pr_ownership_is_unique():
    data = load_inventory()
    direct = {}
    for item in data["capabilities"]:
        for ref in item["references"]:
            if ref.get("type") == "pr" and str(ref.get("state", "")).startswith("open") and ref.get("role") != "integration_batch":
                number = ref.get("number")
                if number is not None:
                    assert number not in direct, f"PR #{number} has multiple direct owners"
                    direct[number] = item["id"]


def test_capability_status_exposes_real_frontier():
    result = CliRunner().invoke(main, ["capability", "status", "stage1c.ode", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["implementation_state"] == "preserved_out_of_order"
    assert any(ref.get("number") == 114 for ref in payload["references"])


def test_capability_next_prioritizes_first_remaining_stage1b_capability():
    result = CliRunner().invoke(main, ["capability", "next", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_action"]["action"] == "implement"
    assert payload["next_action"]["capability_id"] == "stage1b.series_expansions"


def test_capabilities_exposes_control_plane():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["development_control_plane"]["valid"] is True
    assert payload["development_control_plane"]["capability_count"] >= 10


def test_invalid_status_is_rejected():
    result = CliRunner().invoke(main, ["capability", "status", "does.not.exist", "--json"])
    assert result.exit_code != 0


def test_scope_guard_allows_maintenance_branches():
    from automate.dev.guard import validate_branch_scope

    assert validate_branch_scope("fix/ftc-decorator", ["automate/backend/sympy_backend.py"]) == []
    assert validate_branch_scope("hotfix/security-regression", ["automate/backend/sympy_backend.py"]) == []
    assert validate_branch_scope("docs/one-giant-truth", ["docs/ONE_GIANT_TRUTH.md"]) == []
    assert validate_branch_scope("chore/control-plane", ["docs/CAPABILITY_INVENTORY.json"]) == []


def test_scope_guard_rejects_unregistered_capability_branch():
    from automate.dev.guard import validate_branch_scope

    errors = validate_branch_scope("feat/unregistered-capability", ["tests/test_new.py"])
    assert errors
    assert "ownership record" in errors[0]


def test_capability_next_does_not_leapfrog_blocked_dependency():
    from automate.dev.inventory import next_action

    data = {
        "capabilities": [
            {
                "id": "a", "order": 10, "stage": "1A", "name": "A",
                "implementation_state": "planned", "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [], "depends_on": ["b"], "canonical_files": [],
                "shared_integration_points": [], "verification": {"merged_main": False},
                "safe_to_delete": False,
            },
            {
                "id": "b", "order": 20, "stage": "1A", "name": "B",
                "implementation_state": "awaiting_reconciliation", "authority": {"kind": "branch", "ref": "PR1"},
                "references": [{"type": "pr", "number": 1, "state": "open", "branch": "feat/b"}],
                "depends_on": [], "canonical_files": [],
                "shared_integration_points": [], "verification": {"merged_main": False},
                "safe_to_delete": False,
            },
        ]
    }
    payload = next_action(data)
    assert payload["action"] == "blocked"
    assert payload["capability_id"] == "a"
    assert payload["blocked_by"] == ["b"]


def test_capability_next_filters_active_packets_by_dependencies():
    from automate.dev.inventory import next_action

    data = load_inventory()
    payload = next_action(data)
    assert payload["action"] == "implement"
    assert payload["capability_id"] == "stage1b.series_expansions"


def test_preserved_work_does_not_satisfy_dependency():
    from automate.dev.inventory import next_unclaimed

    data = {
        "capabilities": [
            {
                "id": "future", "order": 20, "stage": "1C", "name": "Future",
                "implementation_state": "planned",
                "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [], "depends_on": ["preserved"],
                "canonical_files": [], "shared_integration_points": [],
                "verification": {"merged_main": False}, "safe_to_delete": False,
            },
            {
                "id": "preserved", "order": 10, "stage": "1C", "name": "Preserved",
                "implementation_state": "preserved_out_of_order",
                "authority": {"kind": "branch", "ref": "PR1"},
                "references": [{"type": "pr", "number": 1, "state": "closed_future_work"}],
                "depends_on": [], "canonical_files": [],
                "shared_integration_points": [],
                "verification": {"merged_main": False}, "safe_to_delete": False,
            },
        ]
    }
    assert next_unclaimed(data) is None


def test_tracked_planned_capability_remains_claimable():
    from automate.dev.inventory import next_action, next_unclaimed

    data = load_inventory()
    action = next_action(data)
    assert action["action"] == "implement"
    assert action["capability_id"] == "stage1b.series_expansions"
    candidate = next_unclaimed(data)
    assert candidate is not None
    assert candidate["id"] == "stage1b.series_expansions"


def test_queue_command_exposes_active_and_blocked_state():
    result = CliRunner().invoke(main, ["capability", "queue", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_action"]["action"] == "implement"
    assert payload["next_action"]["capability_id"] == "stage1b.series_expansions"
    assert payload["next_unclaimed"] == "stage1b.series_expansions"
    assert "stage1c.ode" in payload["preserved_out_of_order"]


def test_live_audit_accepts_matching_pr_inventory():
    from automate.dev.live import audit_live

    data = load_inventory()
    item = next(x for x in data["capabilities"] if x["implementation_state"] == "merged_main")
    assert audit_live("rynahmed101-sys/automate", pull_requests=[]) == []


def test_live_audit_rejects_unrecorded_capability_pr():
    from automate.dev.live import audit_live

    with_errors = [
        {
            "number": 999,
            "headRefName": "feat/unrecorded-capability",
            "headRefOid": "0" * 40,
            "baseRefName": "main",
            "isDraft": False,
            "url": "https://github.com/rynahmed101-sys/automate/pull/999",
        }
    ]
    errors = audit_live("rynahmed101-sys/automate", pull_requests=with_errors)
    assert any("no capability ownership reference" in error for error in errors)


def test_live_audit_allows_mutable_active_pr_head():
    from automate.dev.live import audit_live

    pr = {
        "number": 118,
        "headRefName": "integrate/control-plane-live-audit",
        "headRefOid": "f" * 40,
        "baseRefName": "main",
        "isDraft": False,
    }
    assert audit_live("rynahmed101-sys/automate", pull_requests=[pr]) == []


def test_live_audit_accepts_matching_integration_pr():
    from automate.dev.live import audit_live

    pr = {
        "number": 118,
        "headRefName": "integrate/control-plane-live-audit",
        "headRefOid": "0a0d80bf0d7c3a08c2a04a0db78cbb70b11a7f5f",
        "baseRefName": "main",
        "isDraft": False,
    }
    assert audit_live("rynahmed101-sys/automate", pull_requests=[pr]) == []


def test_live_audit_rejects_feature_pr_targeting_non_main():
    from automate.dev.live import audit_live

    pr = {
        "number": 999,
        "headRefName": "feat/unrecorded-capability",
        "headRefOid": "0" * 40,
        "baseRefName": "feature/old-base",
        "isDraft": False,
    }
    errors = audit_live("rynahmed101-sys/automate", pull_requests=[pr])
    assert any("no capability ownership reference" in error for error in errors)


def test_live_audit_allows_registered_control_plane_pr_on_engine():
    from automate.dev.live import audit_live

    pr = {
        "number": 147,
        "headRefName": "feat/operating-mode-contract-20261007",
        "headRefOid": "06bb14b14fcf54c0b04db67edb20d3ee897606",
        "baseRefName": "engine",
        "isDraft": False,
    }
    assert audit_live("rynahmed101-sys/automate", pull_requests=[pr]) == []


def test_live_audit_rejects_capability_pr_on_engine():
    from automate.dev.live import audit_live

    pr = {
        "number": 999,
        "headRefName": "feat/registered-capability",
        "headRefOid": "0" * 40,
        "baseRefName": "engine",
        "isDraft": False,
    }
    errors = audit_live("rynahmed101-sys/automate", pull_requests=[pr])
    assert any("no capability or control-plane ownership reference" in error for error in errors)


def test_live_audit_current_pr_ignores_unrelated_later_prs():
    from automate.dev.live import audit_live

    prs = [
        {
            "number": 201,
            "headRefName": "feat/registered-capability",
            "headRefOid": "1" * 40,
            "baseRefName": "main",
            "isDraft": False,
        },
        {
            "number": 202,
            "headRefName": "feat/unrelated-control-plane",
            "headRefOid": "2" * 40,
            "baseRefName": "main",
            "isDraft": False,
        },
    ]
    errors = audit_live(
        "rynahmed101-sys/automate",
        pull_requests=prs,
        current_pr_number=202,
        base_branch="main",
    )
    assert any("PR #202" in error for error in errors)
    assert not any("PR #201" in error for error in errors)


def test_live_audit_engine_lane_is_not_mistaken_for_canonical_capability_lane():
    from automate.dev.live import audit_live

    pr = {
        "number": 203,
        "headRefName": "feat/engine-control-plane",
        "headRefOid": "3" * 40,
        "baseRefName": "engine",
        "isDraft": False,
    }
    assert audit_live(
        "rynahmed101-sys/automate",
        pull_requests=[pr],
        current_pr_number=203,
        base_branch="engine",
    ) == []


def test_live_audit_full_main_scope_ignores_engine_work():
    from automate.dev.live import audit_live

    prs = [
        {
            "number": 204,
            "headRefName": "feat/engine-control-plane",
            "headRefOid": "4" * 40,
            "baseRefName": "engine",
            "isDraft": False,
        }
    ]
    assert audit_live(
        "rynahmed101-sys/automate",
        pull_requests=prs,
        base_branch="main",
    ) == []
