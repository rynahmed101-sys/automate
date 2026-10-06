"""Bounded autonomous scheduler for Automate.

This loop is intentionally a wake-up mechanism, not a new authority layer.
Each cycle delegates the actual decision to the existing supervisor/autonomous
cycle and records learning. A scheduler can invoke it from a service, CI, or
Chanfana-controlled worker. The default is safe and bounded.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from automate.dev.autonomous import run_autonomous_cycle


class AutonomousLoopError(RuntimeError):
    """Raised when the bounded autonomous loop cannot continue safely."""


def run_bounded_loop(
    repository: str,
    *,
    learning_db: str | Path | None = None,
    worker_url: str | None = None,
    worker_token: str | None = None,
    execute_worker: bool = False,
    max_cycles: int = 1,
    interval_seconds: float = 0.0,
    cycle_fn: Callable[..., dict[str, Any]] = run_autonomous_cycle,
) -> list[dict[str, Any]]:
    if not 1 <= int(max_cycles) <= 100:
        raise AutonomousLoopError("max_cycles must be between 1 and 100")
    if interval_seconds < 0 or interval_seconds > 3600:
        raise AutonomousLoopError("interval_seconds must be between 0 and 3600")

    results: list[dict[str, Any]] = []
    for index in range(int(max_cycles)):
        try:
            result = cycle_fn(
                repository,
                worker_url=worker_url,
                worker_token=worker_token,
                execute_worker=execute_worker,
                learning_db=learning_db,
            )
        except Exception as exc:
            results.append({
                "cycle": index + 1,
                "status": "error",
                "error": str(exc),
            })
            break
        results.append({"cycle": index + 1, "status": result.get("status", "unknown"), "result": result})
        if index + 1 < int(max_cycles) and interval_seconds:
            time.sleep(interval_seconds)
    return results
