"""Machine-readable capability inventory and control-plane validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs" / "CAPABILITY_INVENTORY.json"
SCHEMA_PATH = ROOT / "schemas" / "automate-capability-inventory-v1.json"

ACTIVE_STATES = {"delegated", "awaiting_reconciliation", "reconciled"}
TERMINAL_STATES = {"merged_main", "superseded", "preserved_out_of_order", "abandoned"}


class InventoryError(ValueError):
    """Raised for an inconsistent capability inventory."""


def validate_inventory(data: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [
        f"{list(err.path) or '$'}: {err.message}"
        for err in Draft202012Validator(schema).iter_errors(data)
    ]
    if errors:
        return errors

    records = data["capabilities"]
    by_id = {item["id"]: item for item in records}
    if len(by_id) != len(records):
        errors.append("duplicate capability id")
    orders = [item["order"] for item in records]
    if len(set(orders)) != len(orders):
        errors.append("duplicate capability order")

    for item in records:
        cid = item["id"]
        for dep in item["depends_on"]:
            if dep not in by_id:
                errors.append(f"{cid}: unknown dependency '{dep}'")
            elif by_id[dep]["order"] >= item["order"]:
                errors.append(f"{cid}: dependency '{dep}' is not earlier in the ladder")
        if cid in item["depends_on"]:
            errors.append(f"{cid}: self dependency")
        state = item["implementation_state"]
        v = item["verification"]
        if state == "merged_main" and item["authority"]["kind"] not in {"main", "main_merge"}:
            errors.append(f"{cid}: merged_main must name main authority")
        if state in ACTIVE_STATES:
            has_open = any(ref.get("type") == "pr" and str(ref.get("state", "")).startswith("open") for ref in item["references"])
            if not has_open:
                errors.append(f"{cid}: active state requires an open PR reference")
        if item["safe_to_delete"] and not (state in {"superseded", "abandoned"} or item.get("preserved_in")):
            errors.append(f"{cid}: safe_to_delete requires a preservation record")
        if v.get("certified") and (
            state != "merged_main"
            or not v.get("merged_main")
            or not v.get("exact_head_verified")
            or not v.get("security_audit_verified")
        ):
            errors.append(f"{cid}: certified requires merged main plus exact-head and security evidence")

    direct_owners: dict[int, str] = {}
    for item in records:
        for ref in item["references"]:
            if ref.get("type") != "pr" or not str(ref.get("state", "")).startswith("open"):
                continue
            if ref.get("role") == "integration_batch":
                continue
            number = ref.get("number")
            if isinstance(number, int):
                old = direct_owners.get(number)
                if old and old != item["id"]:
                    errors.append(f"PR #{number}: direct ownership collision between '{old}' and '{item['id']}'")
                direct_owners[number] = item["id"]
    return errors


def load_inventory() -> dict[str, Any]:
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    errors = validate_inventory(data)
    if errors:
        raise InventoryError("; ".join(errors))
    return data


def get_capability(capability_id: str) -> dict[str, Any]:
    for item in load_inventory()["capabilities"]:
        if item["id"] == capability_id:
            return item
    raise InventoryError(f"Unknown capability '{capability_id}'")


def active_references(data: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in data["capabilities"]:
        if item["implementation_state"] not in ACTIVE_STATES:
            continue
        for ref in item["references"]:
            if ref.get("type") == "pr" and str(ref.get("state", "")).startswith("open"):
                result.append({"capability_id": item["id"], **ref})
    return result


def next_action(data: dict[str, Any]) -> dict[str, Any]:
    unresolved = [
        x for x in sorted(data["capabilities"], key=lambda x: x["order"])
        if x["implementation_state"] not in TERMINAL_STATES and x["stage"] != "7"
    ]
    if not unresolved:
        return {"action": "none", "reason": "No unresolved pre-Stage-7 work is recorded."}
    earliest_band = unresolved[0]["order"] // 100
    same_band = [x for x in unresolved if x["order"] // 100 == earliest_band]
    active = [x for x in same_band if x["implementation_state"] in ACTIVE_STATES]
    if active:
        return {
            "action": "reconcile",
            "reason": "Existing earlier-stage packets must be reconciled before new capability delegation.",
            "capability_ids": [x["id"] for x in active],
        }
    return {
        "action": "implement",
        "reason": "No active packet exists in the earliest incomplete band.",
        "capability_id": same_band[0]["id"],
    }


def next_unclaimed(data: dict[str, Any]) -> dict[str, Any] | None:
    for item in sorted(data["capabilities"], key=lambda x: x["order"]):
        if item["implementation_state"] == "planned" and not item["references"]:
            return item
    return None


def summarize() -> dict[str, Any]:
    try:
        data = load_inventory()
    except Exception as exc:
        return {"schema_version":"automate.capability_inventory.v1","valid":False,"errors":[str(exc)]}
    counts: dict[str, int] = {}
    for item in data["capabilities"]:
        counts[item["implementation_state"]] = counts.get(item["implementation_state"], 0) + 1
    candidate = next_unclaimed(data)
    return {
        "schema_version": data["schema_version"],
        "valid": True,
        "authoritative_branch": data["authoritative_branch"],
        "capability_count": len(data["capabilities"]),
        "state_counts": counts,
        "active_reference_count": len(active_references(data)),
        "next_action": next_action(data),
        "next_unclaimed": candidate["id"] if candidate else None,
        "inventory_file": "docs/CAPABILITY_INVENTORY.json",
        "schema_file": "schemas/automate-capability-inventory-v1.json",
    }


def packet(capability_id: str) -> dict[str, Any]:
    item = get_capability(capability_id)
    return {
        "capability": item["id"],
        "stage": item["stage"],
        "name": item["name"],
        "implementation_state": item["implementation_state"],
        "authority": item["authority"],
        "dependencies": item["depends_on"],
        "canonical_files": item["canonical_files"],
        "shared_integration_points": item["shared_integration_points"],
        "references": item["references"],
        "verification_required": item["verification"],
        "safe_to_delete": item["safe_to_delete"],
        "notes": item.get("notes"),
        "agent_contract": {
            "feature_rule": "Use feat/ branches for isolated capability packets; use integrate/ branches for controlled reconciliation.",
            "shared_integration_rule": "Do not modify shared integration files from a capability packet unless the packet itself is an integration branch.",
            "authority_rule": "An unmerged branch is an implementation container, never an authoritative merged-main state.",
        },
    }
