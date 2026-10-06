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
    assert any(ref.get("number") == 105 for ref in payload["references"])


def test_capability_next_prioritizes_active_stage1b_reconciliation():
    result = CliRunner().invoke(main, ["capability", "next", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_action"]["action"] == "reconcile"
    assert "stage1b.fundamental_theorem" in payload["next_action"]["capability_ids"]


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


def test_scope_guard_rejects_unregistered_capability_branch():
    from automate.dev.guard import validate_branch_scope

    errors = validate_branch_scope("feat/unregistered-capability", ["tests/test_new.py"])
    assert errors
    assert "ownership record" in errors[0]
