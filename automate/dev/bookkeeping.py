"""Canonical post-merge bookkeeping for the autonomous capability queue."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


class BookkeepingError(RuntimeError):
    pass


def _env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise BookkeepingError("GH_TOKEN or GITHUB_TOKEN is required")
    return env


def _run(root: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False, env=_env())
    if check and result.returncode != 0:
        raise BookkeepingError(result.stderr.strip() or result.stdout.strip() or "git/gh command failed")
    return result


def _exact_main_evidence(repository: str, sha: str) -> bool:
    result = _run(
        Path.cwd(),
        ["gh", "api", f"repos/{repository}/actions/runs?head_sha={sha}&per_page=100"],
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return False
    successful = {
        str(run.get("name"))
        for run in payload.get("workflow_runs", [])
        if run.get("head_sha") == sha
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    }
    return {"Automate CI", "Security Audit"} <= successful


def _closed_worker_prs(repository: str) -> list[dict[str, Any]]:
    result = _run(
        Path.cwd(),
        [
            "gh", "pr", "list", "--repo", repository, "--state", "closed",
            "--base", "main", "--limit", "100",
            "--json", "number,headRefName,headRefOid,baseRefOid,body,title,mergedAt,mergeCommit,url",
        ],
        check=False,
    )
    if result.returncode != 0:
        return []
    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("mergedAt")]


def find_merged_worker(repository: str, capability_id: str) -> dict[str, Any] | None:
    for pr in _closed_worker_prs(repository):
        body = str(pr.get("body") or "")
        branch = str(pr.get("headRefName") or "")
        match = re.search(r"(?m)^- capability:\s*" + re.escape(capability_id) + r"\s*$", body)
        if match and branch.startswith("feat/" + capability_id + "-"):
            merge_commit = pr.get("mergeCommit") or {}
            merge_sha = str(merge_commit.get("oid") or "")
            if len(merge_sha) == 40:
                return {**pr, "merge_sha": merge_sha}
    return None


def create_bookkeeping_pr(
    repository: str,
    *,
    root: Path,
    capability_id: str,
    worker_pr: dict[str, Any],
) -> dict[str, Any]:
    merge_sha = str(worker_pr["merge_sha"])
    main_ref = _run(root, ["git", "fetch", "origin", "main"], check=True)
    main_sha = _run(root, ["git", "rev-parse", "refs/remotes/origin/main"], check=True).stdout.strip()
    if main_sha != merge_sha and not _run(root, ["git", "merge-base", "--is-ancestor", merge_sha, main_sha]).returncode == 0:
        raise BookkeepingError("worker merge is not contained in current authoritative main")

    if not _exact_main_evidence(repository, merge_sha):
        return {
            "status": "waiting_for_exact_main_evidence",
            "capability_id": capability_id,
            "merge_sha": merge_sha,
        }

    inventory_path = root / "docs/CAPABILITY_INVENTORY.json"
    ledger_path = root / "docs/PROJECT_PHASE_LEDGER.md"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    item = next((x for x in inventory["capabilities"] if x["id"] == capability_id), None)
    if item is None:
        raise BookkeepingError(f"unknown capability in inventory: {capability_id}")

    item["implementation_state"] = "merged_main"
    item["authority"] = {"kind": "main_merge", "ref": merge_sha}
    item["verification"].update({
        "locally_tested": True,
        "development_ci_verified": True,
        "merged_main": True,
        "exact_head_verified": True,
        "security_audit_verified": True,
    })
    item["references"] = [
        *item.get("references", []),
        {
            "type": "pr",
            "number": int(worker_pr["number"]),
            "state": "merged",
            "role": "worker_generated",
            "branch": str(worker_pr["headRefName"]),
            "merge_sha": merge_sha,
        },
    ]

    inventory_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    ledger = ledger_path.read_text(encoding="utf-8")
    name = str(item["name"])
    ledger = ledger.replace("- [ ] " + name, "- [!] " + name)
    frontier = "**Control-plane frontier:** the next claimable Stage 1B capability is **Taylor / Maclaurin series and higher-order expansions** (GitHub issue #141)."
    if capability_id == "stage1b.series_expansions":
        ledger = ledger.replace(
            frontier,
            "**Control-plane frontier:** the next claimable Stage 1B capability is the earliest remaining calculus item after Series; the machine-readable capability inventory is authoritative for the exact next claim."
        )
        ledger = ledger.replace(
            "The next claimable capability is Series expansions (Issue #141).",
            "Series expansions are now implemented/merged; the machine-readable capability inventory determines the next claimable calculus capability."
        )
    ledger_path.write_text(ledger, encoding="utf-8")

    branch = "integrate/auto-bookkeep-" + merge_sha[:12]
    _run(root, ["git", "switch", "-C", branch, main_sha], check=True)
    _run(root, ["git", "add", "--", "docs/CAPABILITY_INVENTORY.json", "docs/PROJECT_PHASE_LEDGER.md"], check=True)
    _run(root, ["git", "commit", "-m", "chore: record autonomous capability promotion"], check=True)
    commit_sha = _run(root, ["git", "rev-parse", "HEAD"], check=True).stdout.strip()
    _run(root, ["git", "push", "--set-upstream", "origin", branch], check=True)

    body = "\n".join([
        "Automated canonical bookkeeping generated after an exact-head verified worker merge.",
        "",
        f"- capability: {capability_id}",
        f"- merge_sha: {merge_sha}",
        f"- bookkeeping_head_sha: {commit_sha}",
        "- automation_role: canonical_bookkeeping",
        "- worker_self_certification: false",
        "- independent_cross_check: pending",
    ])
    created = _run(
        root,
        [
            "gh", "pr", "create", "--repo", repository,
            "--head", branch, "--base", "main",
            "--title", "chore: record autonomous capability promotion",
            "--body", body,
        ],
        check=True,
    )
    return {
        "status": "bookkeeping_pr_created",
        "capability_id": capability_id,
        "merge_sha": merge_sha,
        "bookkeeping_head_sha": commit_sha,
        "pr_url": created.stdout.strip(),
    }
