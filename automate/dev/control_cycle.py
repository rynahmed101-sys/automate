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
from automate.dev.promotion import (
    PromotionError,
    _gh_json,
    find_worker_handoff,
    inspect_worker_handoff_pr,
    inspect_capability_lifecycle,
    execute_promotion,
    find_bookkeeping_pr,
    inspect_bookkeeping_pr,
)

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
    execute_discovery: bool = False,
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
        if not execute_discovery:
            return {**control, "discovery_grant": grant, "dispatch_allowed": False}
        import os
        enabled = os.getenv("AUTOMATE_MIRROR_DISCOVERY_ENABLED", "").strip().lower() in {"1", "true", "yes"}
        if not enabled:
            return {
                **control,
                "discovery_grant": grant,
                "dispatch_allowed": False,
                "status": "mirror_discovery_disabled_by_governance",
            }
        from automate.dev.mirror_discovery_client import dispatch_mirror_discovery, MirrorDiscoveryError
        try:
            result = dispatch_mirror_discovery(
                grant,
                max_tool_steps=6,
            )
        except MirrorDiscoveryError as exc:
            return {
                **control,
                "discovery_grant": grant,
                "dispatch_allowed": False,
                "status": "mirror_discovery_dispatch_blocked",
                "error": str(exc),
            }
        from automate.dev.discovery import triage_mirror_autopilot_result
        from automate.dev.future_capability import build_future_capability_proposal

        triage = triage_mirror_autopilot_result(result.get("result", result))
        if len(triage) > 1:
            return {
                **control,
                "discovery_grant": grant,
                "dispatch_allowed": False,
                "status": "mirror_discovery_protocol_violation",
                "discovery": result,
                "error": "Mirror returned more than one candidate in a one-candidate discovery cycle.",
            }

        future_capability = None
        if triage and triage[0]["status"] == "READY_FOR_INVESTIGATION":
            proposals = __import__("automate.dev.discovery", fromlist=["extract_candidate_proposals"]).extract_candidate_proposals(
                result.get("result", result)
            )
            if proposals:
                future_capability = build_future_capability_proposal(
                    proposals[0],
                    triage[0],
                )

        return {
            **control,
            "discovery_grant": grant,
            "dispatch_allowed": True,
            "status": "mirror_discovery_dispatched",
            "discovery": result,
            "candidate_triage": triage,
            "future_capability": future_capability,
            "canonical_mutation_performed": False,
        }
    if control["mode"] != "BACKLOG":
        return control

    action = control["queue"]["next_action"]
    if action["action"] != "implement":
        return {
            **control,
            "status": "awaiting_reconciliation_or_manual_repair",
            "dispatch_allowed": False,
        }

    from automate.dev.promotion import (
        PromotionError,
        _gh_json,
        find_worker_handoff,
        inspect_worker_handoff_pr,
        inspect_capability_lifecycle,
        execute_promotion,
        execute_bookkeeping_promotion,
        inspect_bookkeeping_pr,
    )

    capability_id = action["capability_id"]

    try:
        ref_payload = _gh_json(repository, "/git/ref/heads/main")
        current_main_sha = str(ref_payload.get("object", {}).get("sha") or "")
    except PromotionError as exc:
        return {
            **control,
            "status": "main_sha_unavailable",
            "error": str(exc),
            "dispatch_allowed": False,
        }

    if len(current_main_sha) != 40:
        return {**control, "status": "main_sha_unavailable", "dispatch_allowed": False}

    # First-class handoff check: an existing worker PR is durable work.
    # Never dispatch a second job for the same canonical capability while that
    # handoff exists, even if inventory bookkeeping has not caught up yet.
    # Detect a previously merged worker handoff even if canonical inventory
    # bookkeeping has not yet caught up.
    try:
        merged_handoff = __import__("automate.dev.promotion", fromlist=["inspect_merged_worker_handoff"]).inspect_merged_worker_handoff(
            repository,
            capability_id=capability_id,
            current_main_sha=current_main_sha,
        )
    except PromotionError as exc:
        return {
            **control,
            "status": "merged_handoff_inspection_error",
            "error": str(exc),
            "dispatch_allowed": False,
        }

    if merged_handoff is not None:
        post = merged_handoff.get("post_merge", {})
        if post.get("state") == "BLOCKED_STALE_MAIN":
            return {
                **control,
                "status": "post_merge_reconciliation_required",
                "dispatch_allowed": False,
                "lifecycle": merged_handoff,
            }
        if post.get("state") == "BOOKKEEPING_READY":
            bookkeeping_pr = inspect_bookkeeping_pr(
                repository,
                capability_id=capability_id,
                merge_sha=current_main_sha,
                require_review=True,
            )
            if bookkeeping_pr and bookkeeping_pr.get("state") == "READY_TO_MERGE":
                import os
                should_execute = os.getenv("AUTOMATE_AUTO_BOOKKEEP", "").strip().lower() in {"1", "true", "yes"}
                bookkeeping_pr["promotion_execution"] = execute_bookkeeping_promotion(
                    repository,
                    int(bookkeeping_pr["pr"]["number"]),
                    current_main_sha=current_main_sha,
                    execute=should_execute,
                )
                return {
                    **control,
                    "status": "bookkeeping_promotion_attempted",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "bookkeeping": bookkeeping_pr,
                }

            if bookkeeping_pr and bookkeeping_pr.get("state") == "STALE_BOOKKEEPING_PR":
                return {
                    **control,
                    "status": "bookkeeping_reconciliation_required",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "bookkeeping": bookkeeping_pr,
                }

            if bookkeeping_pr and bookkeeping_pr.get("state") in {"BLOCKED", "BLOCKED_BOOKKEEPING_SCOPE"}:
                return {
                    **control,
                    "status": "bookkeeping_blocked",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "bookkeeping": bookkeeping_pr,
                }

            if local_root is None:
                return {
                    **control,
                    "status": "bookkeeping_ready",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "next_step": "provide the canonical checkout root to publish the bookkeeping PR",
                }
            try:
                from automate.dev.bookkeeping import build_bookkeeping_plan
                from automate.dev.bookkeeping_pr import create_bookkeeping_pr

                root = Path(local_root)
                inventory_text = __import__("subprocess").run(
                    ["git", "show", f"{current_main_sha}:docs/CAPABILITY_INVENTORY.json"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                ledger_text = __import__("subprocess").run(
                    ["git", "show", f"{current_main_sha}:docs/PROJECT_PHASE_LEDGER.md"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                plan = build_bookkeeping_plan(
                    json.loads(inventory_text),
                    ledger_text,
                    capability_id=capability_id,
                    merge_sha=current_main_sha,
                    exact_head_ci_run=int(post.get("ci_run_id") or 0),
                    security_run=int(post.get("security_run_id") or 0),
                    merged_pr_number=int(merged_handoff["pr_number"]),
                )
                bookkeeping = create_bookkeeping_pr(
                    root,
                    repository,
                    capability_id=capability_id,
                    merge_sha=current_main_sha,
                    merged_pr_number=int(merged_handoff["pr_number"]),
                    exact_head_ci_run=int(post.get("ci_run_id") or 0),
                    security_run=int(post.get("security_run_id") or 0),
                    plan=plan,
                )
                return {
                    **control,
                    "status": "bookkeeping_pr_open",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "bookkeeping": bookkeeping,
                }
            except Exception as exc:
                return {
                    **control,
                    "status": "bookkeeping_blocked",
                    "dispatch_allowed": False,
                    "lifecycle": merged_handoff,
                    "error": str(exc),
                }

    try:
        handoff = find_worker_handoff(
            repository,
            capability_id=capability_id,
            current_main_sha=current_main_sha,
        )
    except PromotionError as exc:
        return {
            **control,
            "status": "worker_handoff_error",
            "error": str(exc),
            "dispatch_allowed": False,
        }

    if handoff is not None:
        try:
            packet = build_worker_packet(
                capability_id,
                repository=repository,
                base_sha_claim=current_main_sha,
                development_branch="main",
            )["packet"]
            lifecycle = inspect_worker_handoff_pr(
                repository,
                capability_id=capability_id,
                packet=packet,
                handoff=handoff,
                current_main_sha=current_main_sha,
            )
            promotion = lifecycle.get("promotion", {})
            if promotion.get("state") == "READY_TO_MERGE":
                import os
                should_execute = os.getenv("AUTOMATE_AUTO_PROMOTE", "").strip().lower() in {"1", "true", "yes"}
                lifecycle["promotion_execution"] = execute_promotion(
                    repository,
                    int(lifecycle["pr"]["number"]),
                    current_main_sha=current_main_sha,
                    execute=should_execute,
                )
        except PromotionError as exc:
            return {
                **control,
                "status": "worker_handoff_blocked",
                "error": str(exc),
                "dispatch_allowed": False,
            }

        return {
            **control,
            "status": (
                "promotion_ready"
                if lifecycle.get("promotion", {}).get("state") == "READY_TO_MERGE"
                else lifecycle.get("promotion_execution", {}).get("execution", lifecycle.get("state", "worker_handoff_active")).lower()
                if isinstance(lifecycle.get("promotion_execution"), dict)
                else lifecycle.get("state", "worker_handoff_active").lower()
            ),
            "dispatch_allowed": False,
            "lifecycle": lifecycle,
        }

    try:
        lifecycle = inspect_capability_lifecycle(
            repository,
            capability_id=capability_id,
            current_main_sha=current_main_sha,
        )
    except PromotionError as exc:
        return {
            **control,
            "status": "promotion_lifecycle_error",
            "error": str(exc),
            "dispatch_allowed": False,
        }

    if lifecycle["state"] == "IMPLEMENTATION_PR":
        evaluation = lifecycle["promotion"]
        return {
            **control,
            "status": "promotion_ready" if evaluation["state"] == "READY_TO_MERGE" else "promotion_blocked",
            "dispatch_allowed": False,
            "lifecycle": lifecycle,
        }

    if lifecycle["state"] == "POST_MERGE":
        return {
            **control,
            "status": "post_merge_verification",
            "dispatch_allowed": False,
            "lifecycle": lifecycle,
        }

    result = run_autonomous_cycle(
        repository,
        worker_url=worker_url,
        worker_token=worker_token,
        execute_worker=execute_worker,
        local_root=local_root,
        mode="backlog",
    )

    lifecycle = None
    decision = result.get("decision", {})
    packet = decision.get("worker_packet", {}).get("packet", {})
    commit = result.get("commit", {})
    base_sha = packet.get("repository", {}).get("base_sha_claim")

    if (
        isinstance(commit, dict)
        and commit.get("status") == "committed"
        and isinstance(base_sha, str)
        and local_root is not None
    ):
        from automate.dev.prmgr import create_worker_pr
        from automate.dev.publisher import push_worker_branch

        try:
            push_worker_branch(Path(local_root), branch_name=str(commit["branch"]))
            handoff = create_worker_pr(
                repository,
                branch=str(commit["branch"]),
                capability_id=capability_id,
                title=f"feat: implement {packet['capability']['name']}",
                base_sha=base_sha,
                test_result=commit.get("tests") or {},
                worker_request_id=str(packet["request_id"]),
            )
            lifecycle = {
                "state": "IMPLEMENTATION_PR",
                "capability_id": capability_id,
                "pr": handoff,
                "worker_commit_sha": commit.get("commit_sha"),
            }
        except Exception as exc:
            lifecycle = {
                "state": "WORKER_HANDOFF_BLOCKED",
                "capability_id": capability_id,
                "error": str(exc),
            }
    elif commit.get("status") == "committed":
        lifecycle = {
            "state": "WORKER_COMMITTED_REQUIRES_PUBLISH",
            "capability_id": capability_id,
            "worker_commit_sha": commit.get("commit_sha"),
        }

    return {
        **control,
        "status": (
            "worker_handoff_open"
            if isinstance(lifecycle, dict) and lifecycle.get("state") == "IMPLEMENTATION_PR"
            else "backlog_cycle_completed"
        ),
        "dispatch_allowed": True,
        "cycle": result,
        "lifecycle": lifecycle,
    }
