"""Evaluate whether Automate has earned permission to enable autonomous workers."""

from __future__ import annotations

from typing import Any


REQUIRED_GATES = (
    "worker_contract_tested",
    "worker_api_authenticated_bounded",
    "worker_output_independently_validated",
    "github_lifecycle_exercised",
    "live_control_plane_clean",
    "exact_head_authority_current",
    "end_to_end_dry_run_passed",
)


def evaluate_readiness(evidence: dict[str, Any]) -> dict[str, Any]:
    failures = [
        gate for gate in REQUIRED_GATES
        if evidence.get(gate) is not True
    ]

    return {
        "schema_version": "automate.autonomy_readiness.v1",
        "ready": not failures,
        "gates": {
            gate: bool(evidence.get(gate) is True)
            for gate in REQUIRED_GATES
        },
        "blocking_gates": failures,
        "worker_mode": "enabled" if not failures else "off",
        "policy": (
            "Workers may be enabled only when every required gate is true."
            if failures
            else "Autonomous workers are eligible for bounded activation; merge/certification authority remains gated."
        ),
    }
