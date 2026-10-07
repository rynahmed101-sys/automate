"""Fail-closed validation and application of Mirror frontier proposals."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class FrontierProposalError(RuntimeError):
    pass


def validate_frontier_result(result: dict[str, Any], *, capability_id: str, base_sha: str) -> list[str]:
    errors: list[str] = []
    if result.get("schema_version") != "mirror.frontier_result.v1":
        errors.append("invalid frontier result schema")
    if result.get("authority") != "UNTRUSTED_MIRROR_PROPOSAL":
        errors.append("frontier result authority marker is invalid")
    if result.get("capability_id") != capability_id:
        errors.append("frontier result capability_id mismatch")
    if result.get("base_revision") != base_sha:
        errors.append("frontier result base revision mismatch")
    proposal = result.get("proposal")
    if not isinstance(proposal, dict):
        errors.append("frontier result missing proposal")
    elif not isinstance(proposal.get("diff"), dict):
        errors.append("frontier result missing bounded diff evidence")
    return errors


def apply_frontier_diff(result: dict[str, Any], *, capability_id: str, base_sha: str, repository_root: Path) -> dict[str, Any]:
    errors = validate_frontier_result(result, capability_id=capability_id, base_sha=base_sha)
    if errors:
        raise FrontierProposalError("; ".join(errors))
    diff = result["proposal"]["diff"].get("stdout", "")
    if not isinstance(diff, str) or not diff.strip():
        return {"status": "no_changes", "capability_id": capability_id}
    if len(diff.encode("utf-8")) > 2_000_000:
        raise FrontierProposalError("frontier diff exceeds bounded proposal size")
    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=error"],
        cwd=repository_root,
        input=diff,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if check.returncode != 0:
        raise FrontierProposalError("frontier diff failed git apply --check: " + check.stderr[-4000:])
    applied = subprocess.run(
        ["git", "apply", "--whitespace=error"],
        cwd=repository_root,
        input=diff,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if applied.returncode != 0:
        raise FrontierProposalError("frontier diff application failed: " + applied.stderr[-4000:])
    return {"status": "applied_for_independent_verification", "capability_id": capability_id}
