"""Closed-loop operating mode controller for autonomous development.

The controller is intentionally narrow:
- unfinished canonical work keeps the system in BACKLOG mode;
- only the strict inventory gate selects the next capability;
- once no canonical work remains, the controller can expose DISCOVERY_READY;
- Mirror never decides that the ledger is complete.
"""

from __future__ import annotations

import json
from pathlib import Path

from typing import Any, Literal

from automate.dev.autonomous import run_autonomous_cycle
from automate.dev.inventory import load_inventory, queue_snapshot
from automate.dev.discovery_grant import build_discovery_grant
from automate.dev.worker import build_worker_packet
from automate.dev import failure_recovery
from automate.dev.promotion import (
    PromotionError,
    _gh_json,
    find_worker_handoff,
    inspect_worker_handoff_pr,
    inspect_capability_lifecycle,
    inspect_merged_worker_handoff,
    execute_promotion,
    find_bookkeeping_pr,
    inspect_bookkeeping_pr,
)
from automate.dev.bookkeeping_pr import execute_bookkeeping_promotion

class VerificationError(RuntimeError):
    """Raised when required scientific verification cannot be completed."""


OperatingMode = Literal["BACKLOG", "DISCOVERY_READY", "STOPPED"]


def find_quarantined_worker_handoff(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    """Dynamic seam for the durable repair-hold inspector."""
    return failure_recovery.find_quarantined_worker_handoff(*args, **kwargs)

