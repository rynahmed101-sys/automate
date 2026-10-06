"""Deterministic supervisor decision for autonomous worker dispatch."""

from __future__ import annotations

import subprocess
from typing import Any

from automate.dev.inventory import (
    InventoryError,
    load_inventory,
    next_action,
    queue_snapshot,
)
from automate.dev.live import LiveAuditError, summarize_live
from automate.dev.worker import build_worker_packet


def observed_main_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "refs/remotes/origin/main"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "main"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
    sha = result.stdout.strip()
    return sha if len(sha) == 40 else None


def supervisor_snapshot(
    repository: str,
    *,
    live: bool = True,
    base_sha: str | None = None,
) -> dict[str, Any]:
    data = load_inventory()
    queue = queue_snapshot(data)

    live_state: dict[str, Any]
    if live:
        try:
            live_state = summarize_live(repository)
        except LiveAuditError as exc:
            return {
                "schema_version": "automate.supervisor.v1",
                "action": "stop",
                "reason": "Live GitHub audit could not be completed.",
                "errors": [str(exc)],
                "queue": queue,
                "can_dispatch": False,
            }
    else:
        live_state = {
            "repository": repository,
            "valid": False,
            "errors": ["live audit intentionally skipped"],
        }

    if not live_state["valid"]:
        return {
            "schema_version": "automate.supervisor.v1",
            "action": "stop",
            "reason": "Live repository state is not clean enough to dispatch a worker.",
            "errors": list(live_state["errors"]),
            "queue": queue,
            "live": live_state,
            "can_dispatch": False,
        }

    live_main_sha = base_sha or observed_main_sha()
    if not live_main_sha:
        return {
            "schema_version": "automate.supervisor.v1",
            "action": "stop",
            "reason": "Supervisor could not establish the exact current main SHA.",
            "errors": ["current main SHA is unavailable"],
            "queue": queue,
            "live": live_state,
            "can_dispatch": False,
        }

    action = next_action(data)
    if action["action"] != "implement":
        return {
            "schema_version": "automate.supervisor.v1",
            "action": action["action"],
            "reason": action["reason"],
            "errors": [],
            "queue": queue,
            "live": live_state,
            "can_dispatch": False,
        }

    capability_id = action.get("capability_id")
    if not capability_id:
        raise InventoryError("Supervisor received an implement action without a capability id.")

    packet = build_worker_packet(
        capability_id,
        repository=repository,
        base_sha_claim=live_main_sha,
    )
    return {
        "schema_version": "automate.supervisor.v1",
        "action": "dispatch",
        "reason": "The strict queue gate identifies one earliest ready capability and live GitHub state is clean.",
        "errors": [],
        "queue": queue,
        "live": live_state,
        "can_dispatch": True,
        "capability_id": capability_id,
        "worker_packet": packet,
    }
