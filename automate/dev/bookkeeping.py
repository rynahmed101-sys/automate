"""Fail-closed canonical bookkeeping plan after a verified capability merge."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from automate.dev.inventory import next_action


class BookkeepingError(ValueError):
    """Raised when canonical promotion bookkeeping is ambiguous or unsafe."""


TERMINAL_STATES = {"merged_main", "superseded", "abandoned"}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _significant_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    stop = {
        "and", "the", "of", "for", "with", "where", "other", "general",
        "higher", "order", "without", "arbitrary", "aware", "related",
    }
    return {token for token in normalized.split() if len(token) >= 3 and token not in stop}


def _stage_section_bounds(ledger: str, stage: str) -> tuple[int, int]:
    heading = re.compile(rf"^## {re.escape(stage)}\.", re.MULTILINE)
    match = heading.search(ledger)
    if not match:
        raise BookkeepingError(f"ledger section for stage {stage} is missing")
    next_heading = re.search(r"^## ", ledger[match.end():], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(ledger)
    return match.end(), end


def _ledger_line_for_capability(ledger: str, *, stage: str, name: str) -> str:
    start, end = _stage_section_bounds(ledger, stage)
    section = ledger[start:end]
    wanted = _significant_tokens(name)
    candidates = []
    for line in section.splitlines():
        if re.match(r"^- \[ \] ", line):
            tokens = _significant_tokens(line[6:])
            overlap = len(wanted & tokens)
            if wanted and overlap / len(wanted) >= 0.75:
                candidates.append(line)
    if len(candidates) != 1:
        raise BookkeepingError(
            f"ledger anchor is ambiguous for {name!r}: matched {len(candidates)} unchecked items"
        )
    return candidates[0]

def _next_capability(inventory: Mapping[str, Any], *, completed_id: str) -> Mapping[str, Any] | None:
    projected = json.loads(json.dumps(inventory))
    completed = next(
        (item for item in projected.get("capabilities", []) if item.get("id") == completed_id),
        None,
    )
    if completed is None:
        raise BookkeepingError(f"unknown capability {completed_id}")
    completed["implementation_state"] = "merged_main"
    for ref in completed.get("references", []):
        if ref.get("type") == "pr":
            ref["state"] = "merged"

    decision = next_action(projected)
    candidate_id = decision.get("capability_id")
    if decision.get("action") != "implement" or not candidate_id:
        return None
    return next(
        (item for item in projected.get("capabilities", []) if item.get("id") == candidate_id),
        None,
    )

def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise BookkeepingError(f"{label} expected exactly once, found {count}")
    return text.replace(old, new, 1)


def build_bookkeeping_plan(
    inventory: Mapping[str, Any],
    ledger: str,
    *,
    capability_id: str,
    merge_sha: str,
    exact_head_ci_run: int,
    security_run: int,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", merge_sha):
        raise BookkeepingError("merge SHA must be an exact lowercase 40-character commit")
    if not isinstance(exact_head_ci_run, int) or exact_head_ci_run < 1:
        raise BookkeepingError("exact_head_ci_run must be a positive integer")
    if not isinstance(security_run, int) or security_run < 1:
        raise BookkeepingError("security_run must be a positive integer")

    records = inventory.get("capabilities", [])
    item = next((x for x in records if x.get("id") == capability_id), None)
    if item is None:
        raise BookkeepingError(f"unknown capability {capability_id}")
    if item.get("implementation_state") in TERMINAL_STATES:
        raise BookkeepingError(f"{capability_id} is already terminal")
    if item.get("stage") == "7":
        raise BookkeepingError("discovery-stage candidates require the separate future-capability admission path")

    ledger_line = _ledger_line_for_capability(
        ledger,
        stage=str(item["stage"]),
        name=str(item["name"]),
    )
    next_item = _next_capability(inventory, completed_id=capability_id)

    next_name = (
        f"{next_item['name']} ({next_item['id']})"
        if next_item
        else "no unresolved pre-discovery capability"
    )

    ledger_start, ledger_end = _stage_section_bounds(ledger, str(item["stage"]))
    section = ledger[ledger_start:ledger_end]
    section = _replace_once(
        section,
        ledger_line,
        ledger_line.replace("- [ ] ", "- [x] ", 1),
        label="capability ledger checkbox",
    )

    frontier_pattern = re.compile(
        r"^\*\*Control-plane frontier:\*\*.*$",
        re.MULTILINE,
    )
    frontier_matches = frontier_pattern.findall(section)
    if frontier_matches:
        if len(frontier_matches) != 1:
            raise BookkeepingError("stage control-plane frontier anchor is ambiguous")
        next_frontier = (
            f"**Control-plane frontier:** the next claimable capability is **{next_name}**."
        )
        section = _replace_once(
            section,
            frontier_matches[0],
            next_frontier,
            label="stage control-plane frontier",
        )

    status_pattern = re.compile(r"^\*\*Current status:\*\*.*$", re.MULTILINE)
    status_matches = status_pattern.findall(section)
    if status_matches:
        if len(status_matches) != 1:
            raise BookkeepingError("stage current-status anchor is ambiguous")
        status_line = (
            f"**Current status:** [~] Active. Canonical capability promotion "
            f"requires exact-main verification and Security Audit evidence. "
            f"The next claimable capability is **{next_name}**. "
            f"Out-of-order preserved work cannot bypass the strict ladder."
        )
        section = _replace_once(
            section,
            status_matches[0],
            status_line,
            label="stage current status",
        )

    next_ledger = ledger[:ledger_start] + section + ledger[ledger_end:]
    next_inventory = json.loads(json.dumps(inventory))
    target = next(x for x in next_inventory["capabilities"] if x["id"] == capability_id)
    target["implementation_state"] = "merged_main"
    target["authority"] = {"kind": "main_merge", "ref": merge_sha}
    for ref in target.get("references", []):
        if ref.get("type") == "pr" and str(ref.get("state", "")).startswith("open"):
            ref["state"] = "merged"
            ref["merge_sha"] = merge_sha
    verification = dict(target.get("verification", {}))
    verification.update({
        "merged_main": True,
        "exact_head_verified": True,
        "security_audit_verified": True,
    })
    target["verification"] = verification
    target["verification_evidence"] = {
        "main_sha": merge_sha,
        "exact_head_workflow_run": exact_head_ci_run,
        "security_workflow_run": security_run,
    }

    return {
        "schema_version": "automate.canonical_bookkeeping.v1",
        "capability_id": capability_id,
        "promotion_source_merge_sha": merge_sha,
        "exact_head_ci_run": exact_head_ci_run,
        "security_run": security_run,
        "next_action": next_item["id"] if next_item else None,
        "authority_change": "BOOKKEEPING_PR_ONLY",
        "canonical_mutation_performed": False,
        "changes": [
            {
                "path": "docs/CAPABILITY_INVENTORY.json",
                "before_sha256": _sha(json.dumps(inventory, sort_keys=True, separators=(",", ":"))),
                "content": json.dumps(next_inventory, indent=2) + "\n",
            },
            {
                "path": "docs/PROJECT_PHASE_LEDGER.md",
                "before_sha256": _sha(ledger),
                "content": next_ledger,
            },
        ],
    }
