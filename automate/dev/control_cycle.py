"""Closed-loop operating mode controller for autonomous development.

The controller is intentionally narrow:
- unfinished canonical work keeps the system in BACKLOG mode;
- only the strict inventory gate selects the next capability;
- once no canonical work remains, the controller can expose DISCOVERY_READY;
- Mirror never decides that the ledger is complete.
"""

from __future__ import annotations

import json

from typing import Any, Literal

from automate.dev.autonomous import run_autonomous_cycle
from automate.dev.inventory import load_inventory, queue_snapshot
from automate.dev.discovery_grant import build_discovery_grant

OperatingMode = Literal["BACKLOG", "DISCOVERY_READY", "STOPPED"]


def resolve_operating_mode(data: dict[str, Any] | None = None) -> dict[str, Any]:
    inventory = data or load_inventory()
    queue = queue_snapshot(inventory)
    action = queue["next_action"]["action"]

    if action == "none":
        return {
            "schema_version": "automate.operating_mode.v1",
            "mode": "DISCOVERY_READY",
            "reason": "The canonical capability queue contains no unresolved pre-discovery work.",
            "queue": queue,
            "mirror_discovery_allowed": True,
        }

    return {
        "schema_version": "automate.operating_mode.v1",
        "mode": "BACKLOG",
        "reason": "Canonical backlog work still exists; strict ledger execution remains dominant.",
        "queue": queue,
        "mirror_discovery_allowed": False,
    }


def run_control_cycle(
    repository: str,
    *,
    worker_url: str | None = None,
    worker_token: str | None = None,
    execute_worker: bool = False,
    local_root=None,
) -> dict[str, Any]:
    control = resolve_operating_mode()
    if control["mode"] == "DISCOVERY_READY":
        grant = build_discovery_grant(
            control,
            correlation_id="ctrl_" + __import__("hashlib").sha256(
                json.dumps(control["queue"], sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()[:24],
        )
        return {**control, "discovery_grant": grant, "dispatch_allowed": False}
    if control["mode"] != "BACKLOG":
        return control

    action = control["queue"]["next_action"]
    if action["action"] != "implement":
        return {
            **control,
            "status": "awaiting_reconciliation_or_manual_repair",
            "dispatch_allowed": False,
        }

    result = run_autonomous_cycle(
        repository,
        worker_url=worker_url,
        worker_token=worker_token,
        execute_worker=execute_worker,
        local_root=local_root,
        mode="backlog",
    )
    return {
        **control,
        "status": "backlog_cycle_completed",
        "dispatch_allowed": True,
        "cycle": result,
    }
