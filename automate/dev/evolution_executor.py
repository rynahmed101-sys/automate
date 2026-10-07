"""Safely materialize an adopted mutable evolution plan as a normal GitHub PR."""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from automate.dev.evolution import validate_evolution_plan

FORBIDDEN_PATHS = {
    "docs/PROJECT_PHASE_LEDGER.md",
    "docs/CAPABILITY_INVENTORY.json",
    "schemas/automate-capability-inventory-v1.json",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
}


class EvolutionExecutionError(RuntimeError):
    """Raised when a self-evolution plan cannot be applied safely."""


@dataclass(frozen=True)
class GitHubResponse:
    status: int
    payload: Any


def _github_request(
    *,
    token: str,
    method: str,
    url: str,
    body: Mapping[str, Any] | None = None,
    timeout: float = 30.0,
) -> GitHubResponse:
    payload = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "automate-self-evolution",
    }
    if body is not None:
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                parsed = json.loads(raw or "{}")
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            return GitHubResponse(response.status, parsed)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return GitHubResponse(exc.code, parsed)
    except (URLError, TimeoutError, OSError) as exc:
        raise EvolutionExecutionError(f"GitHub request failed: {exc}") from exc


def _token() -> str:
    value = os.getenv("AUTOMATE_GITHUB_TOKEN", "").strip()
    if not value:
        raise EvolutionExecutionError("AUTOMATE_GITHUB_TOKEN is required")
    return value


def _enabled() -> None:
    if os.getenv("AUTOMATE_SELF_EVOLUTION_ENABLED", "").strip().lower() not in {"1", "true", "yes"}:
        raise EvolutionExecutionError(
            "self-evolution execution is disabled; set AUTOMATE_SELF_EVOLUTION_ENABLED explicitly"
        )


def _repo_parts(repository: str) -> tuple[str, str]:
    match = re.fullmatch(r"([^/]+)/([^/]+)", repository.strip())
    if not match:
        raise EvolutionExecutionError("repository must be owner/name")
    return match.group(1), match.group(2)


def _api_base(repository: str) -> str:
    owner, name = _repo_parts(repository)
    return f"https://api.github.com/repos/{owner}/{name}"


def _require_object(response: GitHubResponse, *, action: str) -> dict[str, Any]:
    if not isinstance(response.payload, dict):
        raise EvolutionExecutionError(f"{action}: GitHub returned a non-object response")
    return response.payload


def _remote_main_sha(token: str, repository: str) -> str:
    response = _github_request(
        token=token,
        method="GET",
        url=_api_base(repository) + "/git/ref/heads/main",
    )
    payload = _require_object(response, action="read main ref")
    if response.status != 200:
        raise EvolutionExecutionError(f"read main ref failed: {payload.get('message', response.status)}")
    sha = payload.get("object", {}).get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise EvolutionExecutionError("GitHub main ref returned an invalid commit SHA")
    return sha


def _remote_tree_sha(token: str, repository: str, commit_sha: str) -> str:
    response = _github_request(
        token=token,
        method="GET",
        url=_api_base(repository) + "/git/commits/" + commit_sha,
    )
    payload = _require_object(response, action="read base commit")
    if response.status != 200:
        raise EvolutionExecutionError(
            f"read base commit failed: {payload.get('message', response.status)}"
        )
    tree_sha = payload.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        raise EvolutionExecutionError("GitHub base commit returned an invalid tree SHA")
    return tree_sha


def _existing_blob_sha(token: str, repository: str, path: str, base_sha: str) -> tuple[int, str | None]:
    response = _github_request(
        token=token,
        method="GET",
        url=_api_base(repository) + "/contents/" + path + "?ref=" + base_sha,
    )
    payload = response.payload if isinstance(response.payload, dict) else {}
    sha = payload.get("sha") if isinstance(payload, dict) else None
    return response.status, sha if isinstance(sha, str) else None


def execute_evolution_plan(
    plan: Mapping[str, Any],
    *,
    repository: str = "rynahmed101-sys/automate",
    token: str | None = None,
    base_branch: str = "main",
    timeout: float = 30.0,
) -> dict[str, Any]:
    _enabled()
    if base_branch != "main":
        raise EvolutionExecutionError("self-evolution executor currently targets main only")
    token = (token or _token()).strip()
    if not token:
        raise EvolutionExecutionError("GitHub token is required")

    plan_errors = validate_evolution_plan(plan)
    if plan_errors:
        raise EvolutionExecutionError("invalid evolution plan: " + "; ".join(plan_errors))
    if plan.get("apply_mode") != "proposal_only":
        raise EvolutionExecutionError("only proposal-only plans may enter this executor")
    if plan.get("kind") == "governance":
        raise EvolutionExecutionError("governance/constitutional changes are not executable")

    base_sha = str(plan.get("base_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise EvolutionExecutionError("plan base_revision must be an exact 40-hex SHA")

    remote_sha = _remote_main_sha(token, repository)
    if remote_sha != base_sha:
        raise EvolutionExecutionError(
            f"stale evolution plan: plan targets {base_sha}, current main is {remote_sha}"
        )

    changes = plan.get("changes")
    if not isinstance(changes, list) or not changes:
        raise EvolutionExecutionError("evolution plan contains no changes")
    if len(changes) > 20:
        raise EvolutionExecutionError("evolution plan exceeds 20-file change limit")

    tree_entries: list[dict[str, str]] = []
    for change in changes:
        if not isinstance(change, Mapping):
            raise EvolutionExecutionError("evolution change is not an object")
        raw_path = str(change.get("path", ""))
        path = raw_path.replace("\\", "/").lstrip("/")
        if raw_path.startswith("/") or any(part in {".", ".."} for part in path.split("/")):
            raise EvolutionExecutionError(f"evolution path is not a safe relative path: {raw_path!r}")
        operation = change.get("operation")
        if path in FORBIDDEN_PATHS:
            raise EvolutionExecutionError(f"evolution executor refuses authority path: {path}")
        if operation not in {"create", "update"}:
            raise EvolutionExecutionError(f"unsupported evolution operation: {operation}")

        status, current_sha = _existing_blob_sha(token, repository, path, base_sha)
        expected_sha = change.get("expected_sha")
        if operation == "create":
            if status != 404:
                raise EvolutionExecutionError(
                    f"create expected file to be absent, but {path} returned HTTP {status}"
                )
        else:
            if status != 200 or current_sha != expected_sha:
                raise EvolutionExecutionError(
                    f"stale or missing update target {path}: expected {expected_sha}, found {current_sha}"
                )

        content = str(change.get("content", ""))
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        blob = _github_request(
            token=token,
            method="POST",
            url=_api_base(repository) + "/git/blobs",
            body={"content": encoded, "encoding": "base64"},
            timeout=timeout,
        )
        blob_payload = _require_object(blob, action=f"create blob {path}")
        if blob.status != 201:
            raise EvolutionExecutionError(
                f"create blob {path} failed: {blob_payload.get('message', blob.status)}"
            )
        blob_sha = blob_payload.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
            raise EvolutionExecutionError(f"GitHub returned invalid blob SHA for {path}")
        tree_entries.append({
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    base_tree_sha = _remote_tree_sha(token, repository, base_sha)
    tree = _github_request(
        token=token,
        method="POST",
        url=_api_base(repository) + "/git/trees",
        body={"base_tree": base_tree_sha, "tree": tree_entries},
        timeout=timeout,
    )
    tree_payload = _require_object(tree, action="create evolution tree")
    if tree.status != 201:
        raise EvolutionExecutionError(
            f"create evolution tree failed: {tree_payload.get('message', tree.status)}"
        )
    tree_sha = tree_payload.get("sha")
    if not isinstance(tree_sha, str):
        raise EvolutionExecutionError("GitHub returned no tree SHA")

    proposal_id = str(plan.get("proposal_id", "unknown"))
    commit = _github_request(
        token=token,
        method="POST",
        url=_api_base(repository) + "/git/commits",
        body={
            "message": "evolution: apply adopted proposal " + proposal_id,
            "tree": tree_sha,
            "parents": [base_sha],
        },
        timeout=timeout,
    )
    commit_payload = _require_object(commit, action="create evolution commit")
    if commit.status != 201:
        raise EvolutionExecutionError(
            f"create evolution commit failed: {commit_payload.get('message', commit.status)}"
        )
    commit_sha = commit_payload.get("sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise EvolutionExecutionError("GitHub returned invalid evolution commit SHA")

    branch_name = "chore/evolution/" + proposal_id
    ref = _github_request(
        token=token,
        method="POST",
        url=_api_base(repository) + "/git/refs",
        body={"ref": "refs/heads/" + branch_name, "sha": commit_sha},
        timeout=timeout,
    )
    ref_payload = _require_object(ref, action="create evolution branch")
    if ref.status != 201:
        raise EvolutionExecutionError(
            f"create evolution branch failed: {ref_payload.get('message', ref.status)}"
        )

    regression_lines = ["- " + str(item) for item in plan.get("regression_requirements", [])]
    body = "\n".join([
        "Automated self-evolution proposal.",
        "",
        "Proposal: " + proposal_id,
        "Base revision: " + base_sha,
        "",
        "This PR was created by the reversible self-evolution executor. It does not self-merge.",
        "",
        "Regression requirements:",
        *regression_lines,
        "",
        "Rollback:",
        str(plan.get("rollback", "")),
        "",
        "Certification remains blocked until the normal CI, Security Audit, exact-head,",
        "reconciliation, and capability-authority lifecycle succeeds.",
    ])
    pr = _github_request(
        token=token,
        method="POST",
        url=_api_base(repository) + "/pulls",
        body={
            "title": "evolution: apply adopted proposal " + proposal_id,
            "head": branch_name,
            "base": "main",
            "body": body,
            "maintainer_can_modify": False,
        },
        timeout=timeout,
    )
    pr_payload = _require_object(pr, action="create evolution PR")
    if pr.status != 201:
        raise EvolutionExecutionError(
            f"create evolution PR failed: {pr_payload.get('message', pr.status)}"
        )

    return {
        "status": "pr_created",
        "proposal_id": proposal_id,
        "repository": repository,
        "base_revision": base_sha,
        "commit_sha": commit_sha,
        "branch": branch_name,
        "pull_request_number": pr_payload.get("number"),
        "pull_request_url": pr_payload.get("html_url"),
        "self_merge": False,
        "certified": False,
    }
