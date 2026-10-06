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
    assert any(ref.get("number") == 92 for ref in payload["references"])


def test_capability_next_advances_to_stage1b_after_stage1a_completion():
    result = CliRunner().invoke(main, ["capability", "next", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_action"]["action"] == "implement"
    assert payload["next_action"]["capability_id"] == "stage1b.fundamental_theorem"


def test_capabilities_exposes_control_plane():
    result = CliRunner().invoke(main, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["development_control_plane"]["valid"] is True
    assert payload["development_control_plane"]["capability_count"] >= 10


def test_invalid_status_is_rejected():
    result = CliRunner().invoke(main, ["capability", "status", "does.not.exist", "--json"])
    assert result.exit_code != 0
