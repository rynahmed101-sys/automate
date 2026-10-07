"""Machine-readable evidence receipts for autonomous development."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from automate.dev.worker import ROOT

EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "automate-evidence-receipt-v1.json"

_TRUST_ORDER = {
    "PLANNED": 0, "IMPLEMENTED": 1, "LOCALLY_TESTED": 2, "IMPLEMENTATION_VERIFIED": 4,
    "DEV_CI_VERIFIED": 3, "MERGED_MAIN": 4, "EXACT_HEAD_VERIFIED": 5,
    "SECURITY_VERIFIED": 6, "INDEPENDENTLY_CROSS_CHECKED": 7, "CERTIFIED": 8,
}

def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return [error.message for error in Draft202012Validator(schema).iter_errors(receipt)]

def build_receipt(*, action: str, repository: str, base_sha: str,
                  trust_state: str, evidence: list[dict[str, Any]],
                  branch: str | None = None, pr_number: int | None = None,
                  merge_sha: str | None = None,
                  unresolved: list[str] | None = None,
                  action_cycle_id: str | None = None,
                  target: str | None = None,
                  capability_id: str | None = None,
                  job_id: str | None = None,
                  experiment_id: str | None = None,
                  run_id: str | None = None,
                  source: dict[str, Any] | None = None,
                  packet_id: str | None = None,
                  result_id: str | None = None,
                  file_hashes: list[dict[str, str]] | None = None,
                  verification: dict[str, Any] | None = None,
                  final_exact_head_sha: str | None = None) -> dict[str, Any]:
    if trust_state not in _TRUST_ORDER:
        raise ValueError(f"unknown trust state: {trust_state}")
    receipt = {
        "schema_version": "automate.evidence_receipt.v1",
        "receipt_id": f"rcpt_{uuid.uuid4().hex}",
        "action": action,
        "repository": {"full_name": repository, "base_sha": base_sha,
                       "branch": branch, "pr_number": pr_number, "merge_sha": merge_sha},
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "trust_state": trust_state,
        "action_cycle_id": action_cycle_id,
        "target": target,
        "capability_id": capability_id,
        "job_id": job_id,
        "experiment_id": experiment_id,
        "run_id": run_id,
        "source": source,
        "packet_id": packet_id,
        "result_id": result_id,
        "file_hashes": list(file_hashes or []),
        "verification": verification or {},
        "final_exact_head_sha": final_exact_head_sha,
        "evidence": {"items": evidence},
        "unresolved": list(unresolved or []),
    }
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors))
    return receipt

def trust_at_least(receipt: dict[str, Any], required_state: str) -> bool:
    current = receipt.get("trust_state")
    return current in _TRUST_ORDER and required_state in _TRUST_ORDER and _TRUST_ORDER[current] >= _TRUST_ORDER[required_state]

def receipt_json(receipt: dict[str, Any]) -> str:
    return json.dumps(receipt, indent=2, sort_keys=True)
