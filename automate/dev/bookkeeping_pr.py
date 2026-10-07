"""Create a reviewable canonical bookkeeping PR from a verified merge."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping


class BookkeepingPrError(RuntimeError):
    """Raised when canonical bookkeeping cannot be safely published."""


def _env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise BookkeepingPrError("GH_TOKEN or GITHUB_TOKEN is required for bookkeeping PR creation")
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
        raise BookkeepingPrError(result.stderr.strip() or "git/gh command failed")
    return result


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _existing_pr(repository: str, branch: str) -> dict[str, Any] | None:
    result = subprocess.run(
        [
            "gh", "pr", "list",
            "--repo", repository,
            "--head", branch,
            "--base", "main",
            "--state", "open",
            "--json", "number,url,headRefName,baseRefName,body",
            "--limit", "10",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    if result.returncode != 0:
        raise BookkeepingPrError(result.stderr.strip() or "unable to inspect existing bookkeeping PRs")
    import json
    rows = json.loads(result.stdout or "[]")
    if not isinstance(rows, list):
        raise BookkeepingPrError("GitHub returned invalid bookkeeping PR list")
    return rows[0] if rows else None


def create_bookkeeping_pr(
    repository_root: Path,
    repository: str,
    *,
    capability_id: str,
    merge_sha: str,
    merged_pr_number: int,
    exact_head_ci_run: int,
    security_run: int,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    if not repository or "/" not in repository:
        raise BookkeepingPrError("repository must be owner/name")
    if not __import__("re").fullmatch(r"[0-9a-f]{40}", merge_sha):
        raise BookkeepingPrError("merge_sha must be an exact lowercase 40-character commit")
    if not isinstance(merged_pr_number, int) or merged_pr_number < 1:
        raise BookkeepingPrError("merged_pr_number must be positive")
    if not plan.get("canonical_mutation_performed") is False:
        raise BookkeepingPrError("bookkeeping plan must be non-mutating until its reviewable PR is merged")
    changes = plan.get("changes")
    if not isinstance(changes, list) or len(changes) != 2:
        raise BookkeepingPrError("bookkeeping plan must contain exactly two canonical file changes")

    fetch = _run(repository_root, ["git", "fetch", "origin", "main"], check=True)
    ref = _run(repository_root, ["git", "rev-parse", "refs/remotes/origin/main"], check=True)
    current = ref.stdout.strip()
    if current != merge_sha:
        raise BookkeepingPrError(
            f"authoritative main moved during bookkeeping preparation: expected {merge_sha}, observed {current}"
        )

    branch = f"integrate/canonical-bookkeeping-{capability_id}-{merge_sha[:12]}"
    if not __import__("re").fullmatch(r"integrate/[a-z0-9_.-]+", branch):
        raise BookkeepingPrError("generated bookkeeping branch name is unsafe")

    existing = _existing_pr(repository, branch)
    if existing:
        return {
            "status": "existing_open",
            "branch": branch,
            "pr": existing,
            "merge_sha": merge_sha,
        }

    tmp = Path(tempfile.mkdtemp(prefix="automate-bookkeeping-"))
    added = _run(
        repository_root,
        ["git", "worktree", "add", "--detach", str(tmp), merge_sha],
        check=True,
    )
    try:
        switched = _run(tmp, ["git", "switch", "-c", branch], check=True)
        for change in changes:
            path = str(change.get("path") or "")
            if path not in {"docs/CAPABILITY_INVENTORY.json", "docs/PROJECT_PHASE_LEDGER.md"}:
                raise BookkeepingPrError(f"unexpected bookkeeping path: {path}")
            expected = str(change.get("before_sha256") or "")
            target = (tmp / path).resolve()
            try:
                target.relative_to(tmp.resolve())
            except ValueError as exc:
                raise BookkeepingPrError(f"bookkeeping path escapes worktree: {path}") from exc
            current_text = target.read_text(encoding="utf-8")
            observed_sha = _sha256_text(
                __import__("json").dumps(__import__("json").loads(current_text), sort_keys=True, separators=(",", ":"))
                if path.endswith(".json")
                else current_text
            )
            if path.endswith(".json"):
                # Inventory plans hash normalized JSON to avoid whitespace ambiguity.
                if observed_sha != expected:
                    raise BookkeepingPrError(f"inventory preimage mismatch for {path}")
            elif observed_sha != expected:
                raise BookkeepingPrError(f"ledger preimage mismatch for {path}")
            target.write_text(str(change.get("content") or ""), encoding="utf-8")
        _run(tmp, ["git", "diff", "--check"], check=True)
        _run(tmp, ["git", "add", "--", "docs/CAPABILITY_INVENTORY.json", "docs/PROJECT_PHASE_LEDGER.md"], check=True)
        commit = _run(
            tmp,
            [
                "git", "commit", "-m",
                f"chore: record verified promotion of {capability_id}",
            ],
            check=True,
        )
        pushed = _run(
            repository_root,
            ["git", "push", "--set-upstream", "origin", branch],
            check=True,
        )
        body = "\n".join([
            "Automated canonical bookkeeping proposal generated after an evidence-gated capability merge.",
            "",
            f"- capability: {capability_id}",
            f"- merged_pr: {merged_pr_number}",
            f"- merge_sha: {merge_sha}",
            f"- exact_head_ci_run: {exact_head_ci_run}",
            f"- security_run: {security_run}",
            "- automation_role: canonical_bookkeeping",
            "- canonical_mutation: proposed_in_reviewable_pr",
            "",
            "This PR contains only inventory/ledger bookkeeping. The merge SHA and evidence above are bound to the exact current main head.",
        ])
        pr = _run(
            repository_root,
            [
                "gh", "pr", "create",
                "--repo", repository,
                "--head", branch,
                "--base", "main",
                "--title", f"chore: record verified promotion of {capability_id}",
                "--body", body,
            ],
            check=True,
        )
        return {
            "status": "created",
            "branch": branch,
            "commit_sha": _run(tmp, ["git", "rev-parse", "HEAD"], check=True).stdout.strip(),
            "pr_url": pr.stdout.strip(),
            "merge_sha": merge_sha,
        }
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tmp)],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
