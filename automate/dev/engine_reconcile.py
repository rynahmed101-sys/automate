"""Safe main-to-engine reconciliation controller for the scheduled control plane.

This is infrastructure synchronization, not scientific capability promotion.
It never force-pushes and never mutates the canonical ledger directly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


class EngineReconcileError(RuntimeError):
    pass


def _env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise EngineReconcileError("GH_TOKEN or GITHUB_TOKEN is required")
    return env


def _run(root: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    if check and result.returncode != 0:
        raise EngineReconcileError(result.stderr.strip() or "git/gh command failed")
    return result


def reconcile_engine(
    root: str | Path,
    repository: str,
    *,
    auto_merge: bool = False,
) -> dict[str, Any]:
    checkout = Path(root).resolve()
    if not checkout.is_dir():
        raise EngineReconcileError("repository checkout root does not exist")
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        raise EngineReconcileError("repository must be owner/name")

    _run(checkout, ["git", "fetch", "origin", "main", "engine"], check=True)
    main_sha = _run(checkout, ["git", "rev-parse", "refs/remotes/origin/main"], check=True).stdout.strip()
    engine_sha = _run(checkout, ["git", "rev-parse", "refs/remotes/origin/engine"], check=True).stdout.strip()

    if not re.fullmatch(r"[0-9a-f]{40}", main_sha) or not re.fullmatch(r"[0-9a-f]{40}", engine_sha):
        raise EngineReconcileError("observed branch SHAs are malformed")

    ancestor = _run(
        checkout,
        ["git", "merge-base", "--is-ancestor", main_sha, engine_sha],
    )
    if ancestor.returncode == 0:
        return {
            "schema_version": "automate.engine_reconcile.v1",
            "state": "ALIGNED",
            "main_sha": main_sha,
            "engine_sha": engine_sha,
            "action": "none",
        }

    branch = f"integrate/auto-main-into-engine-{main_sha[:12]}"
    if not re.fullmatch(r"integrate/auto-main-into-engine-[0-9a-f]{12}", branch):
        raise EngineReconcileError("generated reconciliation branch is unsafe")

    all_open = _run(
        checkout,
        [
            "gh", "pr", "list",
            "--repo", repository,
            "--base", "engine",
            "--state", "open",
            "--json", "number,body,headRefName,headRefOid,baseRefName",
            "--limit", "50",
        ],
        check=True,
    )
    all_rows = json.loads(all_open.stdout or "[]")
    if not isinstance(all_rows, list):
        raise EngineReconcileError("GitHub returned invalid reconciliation PR data")

    current_branch_rows = []
    for row in all_rows:
        if not isinstance(row, dict):
            continue
        head = str(row.get("headRefName") or "")
        if not head.startswith("integrate/auto-main-into-engine-"):
            continue
        body = str(row.get("body") or "")
        match = re.search(r"(?m)^- authoritative_main_sha:\s*([0-9a-f]{40})\s*$", body)
        if match and match.group(1) != main_sha:
            _run(
                checkout,
                [
                    "gh", "pr", "close", str(row.get("number")),
                    "--repo", repository,
                    "--comment", "Superseded by a newer authoritative main frontier.",
                ],
            )
            continue
        current_branch_rows.append(row)

    rows = [
        row for row in current_branch_rows
        if row.get("headRefName") == branch
    ]
    if not isinstance(rows, list):
        raise EngineReconcileError("GitHub returned invalid reconciliation PR data")

    if rows:
        pr = rows[0]
        if auto_merge:
            merge = _run(
                checkout,
                [
                    "gh", "pr", "merge", str(pr["number"]),
                    "--repo", repository,
                    "--auto",
                    "--merge",
                    "--delete-branch=false",
                ],
            )
            if merge.returncode != 0:
                return {
                    "schema_version": "automate.engine_reconcile.v1",
                    "state": "PR_OPEN",
                    "main_sha": main_sha,
                    "engine_sha": engine_sha,
                    "branch": branch,
                    "pr": pr,
                    "action": "awaiting_checks_or_mergeability",
                    "merge_error": merge.stderr.strip(),
                }
            return {
                "schema_version": "automate.engine_reconcile.v1",
                "state": "PR_AUTO_MERGE_REQUESTED",
                "main_sha": main_sha,
                "engine_sha": engine_sha,
                "branch": branch,
                "pr": pr,
                "action": "auto_merge_requested",
            }
        return {
            "schema_version": "automate.engine_reconcile.v1",
            "state": "PR_OPEN",
            "main_sha": main_sha,
            "engine_sha": engine_sha,
            "branch": branch,
            "pr": pr,
            "action": "awaiting_reconciliation_pr",
        }

    _run(checkout, ["git", "switch", "-C", branch, engine_sha], check=True)
    merged = _run(
        checkout,
        ["git", "merge", "--no-ff", "--no-edit", main_sha],
    )
    if merged.returncode != 0:
        _run(checkout, ["git", "merge", "--abort"])
        return {
            "schema_version": "automate.engine_reconcile.v1",
            "state": "CONFLICT",
            "main_sha": main_sha,
            "engine_sha": engine_sha,
            "branch": branch,
            "action": "manual_reconciliation_required",
            "error": merged.stderr.strip() or merged.stdout.strip(),
        }

    new_head = _run(checkout, ["git", "rev-parse", "HEAD"], check=True).stdout.strip()
    _run(checkout, ["git", "push", "--set-upstream", "origin", branch], check=True)
    created = _run(
        checkout,
        [
            "gh", "pr", "create",
            "--repo", repository,
            "--head", branch,
            "--base", "engine",
            "--title", "integrate: automatically reconcile authoritative main into engine",
            "--body",
            "\n".join([
                "Automated engine reconciliation generated by the bounded control plane.",
                "",
                f"- authoritative_main_sha: {main_sha}",
                f"- prior_engine_sha: {engine_sha}",
                f"- reconciliation_head_sha: {new_head}",
                "- automation_role: infrastructure_reconciliation",
                "- canonical_ledger_mutation: false",
                "",
                "This PR only brings engine history forward to contain authoritative main. "
                "It does not implement or certify a scientific capability.",
            ]),
        ],
        check=True,
    )
    pr_url = created.stdout.strip()
    if auto_merge:
        listed = _run(
            checkout,
            [
                "gh", "pr", "list",
                "--repo", repository,
                "--head", branch,
                "--base", "engine",
                "--state", "open",
                "--json", "number",
                "--limit", "1",
            ],
            check=True,
        )
        listed_rows = json.loads(listed.stdout or "[]")
        if listed_rows:
            merge = _run(
                checkout,
                [
                    "gh", "pr", "merge", str(listed_rows[0]["number"]),
                    "--repo", repository,
                    "--auto",
                    "--merge",
                    "--delete-branch=false",
                ],
            )
            if merge.returncode == 0:
                return {
                    "schema_version": "automate.engine_reconcile.v1",
                    "state": "PR_AUTO_MERGE_REQUESTED",
                    "main_sha": main_sha,
                    "engine_sha": engine_sha,
                    "branch": branch,
                    "reconciliation_head_sha": new_head,
                    "pr_url": pr_url,
                    "action": "auto_merge_requested",
                }
    return {
        "schema_version": "automate.engine_reconcile.v1",
        "state": "PR_CREATED",
        "main_sha": main_sha,
        "engine_sha": engine_sha,
        "branch": branch,
        "reconciliation_head_sha": new_head,
        "pr_url": pr_url,
        "action": "await_checks_and_reconciliation_merge",
    }

