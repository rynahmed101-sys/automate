"""Reversible planning boundary for self-evolution changes.

A system-evolution proposal may describe a desired improvement. This module
turns an already-admitted mutable proposal into an exact change plan that can
later be verified and routed through the normal PR/reconciliation path.

It never applies a change, never mutates the ledger, and never permits
constitutional/authority files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from automate.dev.learning import LearningError, validate_evolution_proposal, canonical_json, deterministic_id

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
PLAN_SCHEMA = ROOT / "schemas" / "automate-system-evolution-plan-v1.json"

FORBIDDEN_AUTHORITY_PATHS = {
    "docs/PROJECT_PHASE_LEDGER.md",
    "docs/CAPABILITY_INVENTORY.json",
    "schemas/automate-capability-inventory-v1.json",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
}
ALLOWED_KINDS = {"knowledge", "strategy", "verifier", "capability"}
EVOLUTION_SAFE_ROOTS = ("automate/", "tests/", "schemas/", "docs/")


class EvolutionPlanError(ValueError):
    """Raised when a self-evolution change plan violates the boundary."""


@dataclass(frozen=True)
class EvolutionPlan:
    plan_id: str
    proposal_id: str
    base_revision: str
    kind: str
    allowed_path_prefixes: tuple[str, ...]
    changes: tuple[Mapping[str, Any], ...]
    regression_requirements: tuple[str, ...]
    rollback: str
    apply_mode: str = "proposal_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "automate.system_evolution_plan.v1",
            "plan_id": self.plan_id,
            "proposal_id": self.proposal_id,
            "base_revision": self.base_revision,
            "kind": self.kind,
            "allowed_path_prefixes": list(self.allowed_path_prefixes),
            "changes": [dict(x) for x in self.changes],
            "regression_requirements": list(self.regression_requirements),
            "rollback": self.rollback,
            "apply_mode": self.apply_mode,
        }


def _under_prefix(path: str, prefixes: Iterable[str]) -> bool:
    normalized = str(path).replace("\\", "/").lstrip("/")
    return any(
        normalized == prefix.rstrip("/")
        or normalized.startswith(prefix.rstrip("/") + "/")
        for prefix in prefixes
    )


def _safe_prefix(prefix: str) -> bool:
    normalized = prefix.replace("\\", "/").lstrip("/").rstrip("/") + "/"
    return any(normalized.startswith(root) for root in EVOLUTION_SAFE_ROOTS)


def _validate_plan(value: Mapping[str, Any]) -> list[str]:
    errors = [
        error.message
        for error in Draft202012Validator(
            __import__("json").loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
        ).iter_errors(value)
    ]
    return errors


def validate_evolution_plan(value: Mapping[str, Any]) -> list[str]:
    """Validate an already-materialized plan at an execution boundary."""
    errors = _validate_plan(value)
    if errors:
        return errors
    prefixes = value.get("allowed_path_prefixes", [])
    changes = value.get("changes", [])
    for change in changes:
        path = str(change.get("path", "")).replace("\\", "/").lstrip("/")
        if not _under_prefix(path, prefixes):
            errors.append(f"change is outside allowed evolution prefixes: {path}")
        if path in FORBIDDEN_AUTHORITY_PATHS:
            errors.append(f"change targets forbidden authority/security path: {path}")
        if ".." in path.split("/"):
            errors.append(f"change contains path traversal segment: {path}")
    return errors


def build_evolution_plan(
    proposal: Mapping[str, Any],
    *,
    base_revision: str,
    allowed_path_prefixes: Iterable[str],
    changes: Iterable[Mapping[str, Any]],
) -> EvolutionPlan:
    proposal_errors = validate_evolution_proposal(proposal)
    if proposal_errors:
        raise EvolutionPlanError("; ".join(proposal_errors))
    if proposal["kind"] not in ALLOWED_KINDS:
        raise EvolutionPlanError("governance/constitutional changes are not plan-applicable")
    if proposal["classification"] != "MUTABLE":
        raise EvolutionPlanError("only MUTABLE evolution proposals can produce a change plan")
    if proposal["status"] != "ADOPTED":
        raise EvolutionPlanError("evolution plan requires an ADOPTED proposal")
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision):
        raise EvolutionPlanError("evolution plan requires an exact 40-character base revision")

    prefixes = tuple(sorted({str(x).replace("\\", "/").rstrip("/") for x in allowed_path_prefixes if str(x).strip()}))
    if not prefixes:
        raise EvolutionPlanError("at least one allowed path prefix is required")
    unsafe_prefixes = [prefix for prefix in prefixes if not _safe_prefix(prefix)]
    if unsafe_prefixes:
        raise EvolutionPlanError(
            "evolution paths must stay under approved repository roots: "
            + ", ".join(unsafe_prefixes)
        )

    changes_tuple = tuple(dict(x) for x in changes)
    if not changes_tuple:
        raise EvolutionPlanError("evolution plan requires at least one change")
    if len(changes_tuple) > 20:
        raise EvolutionPlanError("evolution plan exceeds bounded 20-file change limit")

    for change in changes_tuple:
        path = str(change.get("path", "")).replace("\\", "/").lstrip("/")
        operation = change.get("operation")
        if operation not in {"create", "update"}:
            raise EvolutionPlanError("evolution plan permits create/update only")
        if not _under_prefix(path, prefixes):
            raise EvolutionPlanError(f"change is outside allowed evolution prefixes: {path}")
        if path in FORBIDDEN_AUTHORITY_PATHS:
            raise EvolutionPlanError(f"evolution plan may not modify authority/security path: {path}")
        if operation == "update" and not re.fullmatch(r"[0-9a-f]{40}", str(change.get("expected_sha", ""))):
            raise EvolutionPlanError(f"update requires exact expected_sha: {path}")
        if operation == "create" and change.get("expected_sha") is not None:
            raise EvolutionPlanError(f"create must use null expected_sha: {path}")

    plan = EvolutionPlan(
        plan_id=deterministic_id(
            "evoplan",
            proposal["proposal_id"],
            base_revision,
            list(prefixes),
            list(changes_tuple),
        ),
        proposal_id=str(proposal["proposal_id"]),
        base_revision=base_revision,
        kind=str(proposal["kind"]),
        allowed_path_prefixes=prefixes,
        changes=changes_tuple,
        regression_requirements=tuple(proposal["regression_requirements"]),
        rollback=str(proposal["rollback"]),
    )
    errors = _validate_plan(plan.to_dict())
    if errors:
        raise EvolutionPlanError("; ".join(errors))
    return plan