"""Keep the capability evidence index valid and tied to checked-in files."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[1]


def test_capability_inventory_schema_and_paths():
    schema = json.loads(
        (ROOT / "schemas" / "automate-capability-inventory-v1.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = json.loads(
        (ROOT / "docs" / "CAPABILITY_INVENTORY.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(inventory)

    for capability in inventory["capabilities"]:
        for path in (*capability["canonical_files"], *capability["tests"]):
            assert (ROOT / path).exists(), f"{capability['id']} references missing path: {path}"


def test_capability_inventory_does_not_claim_unverified_branch_evidence():
    inventory = json.loads(
        (ROOT / "docs" / "CAPABILITY_INVENTORY.json").read_text(encoding="utf-8")
    )

    for capability in inventory["capabilities"]:
        verification = capability["verification"]
        if capability["implementation_state"] == "active_development":
            assert verification["merged_main"] is False
            assert verification["exact_head_verified"] is False
            assert verification["security_audit_verified"] is False
        if verification["formally_proved"]:
            assert verification["independently_cross_checked"]
