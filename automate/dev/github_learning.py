"""Read-only GitHub Actions synchronization for the learning ledger."""
from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote

from automate.dev.learning import LearningStore
from automate.dev.learning_events import record_ci_result


class GitHubLearningSyncError(RuntimeError):
    """Raised when GitHub Actions history cannot be synchronized safely."""


def _token(token: str | None = None) -> str:
    value = (token or os.getenv("AUTOMATE_GITHUB_TOKEN") or "").strip()
    if not value:
        raise GitHubLearningSyncError("AUTOMATE_GITHUB_TOKEN is required for GitHub learning sync")
    return value


def _request_json(url: str, *, token: str, timeout: float = 30.0) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "automate-learning-sync",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise GitHubLearningSyncError("GitHub Actions response exceeds bounded 2MB limit")
    except HTTPError as exc:
        raise GitHubLearningSyncError(
            f"GitHub Actions request failed: HTTP {exc.code}"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise GitHubLearningSyncError(
            f"GitHub Actions request failed: {exc}"
        ) from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubLearningSyncError("GitHub Actions returned invalid JSON") from exc
    if not isinstance(payload, Mapping):
        raise GitHubLearningSyncError("GitHub Actions returned a non-object payload")
    return payload


def sync_github_actions(
    store: LearningStore,
    *,
    repository: str = "rynahmed101-sys/automate",
    branch: str = "main",
    limit: int = 20,
    token: str | None = None,
) -> dict[str, Any]:
    if "/" not in repository or not repository.count("/") == 1:
        raise GitHubLearningSyncError("repository must be owner/name")
    if not 1 <= int(limit) <= 100:
        raise GitHubLearningSyncError("limit must be between 1 and 100")

    encoded_branch = quote(branch, safe="")
    encoded_repo = quote(repository, safe="/")
    payload = _request_json(
        f"https://api.github.com/repos/{encoded_repo}/actions/runs"
        f"?branch={encoded_branch}&per_page={int(limit)}",
        token=_token(token),
    )
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise GitHubLearningSyncError("GitHub Actions payload has no workflow_runs array")

    recorded = 0
    skipped = 0
    for run in runs:
        if not isinstance(run, Mapping):
            skipped += 1
            continue
        status = str(run.get("status", "")).lower()
        conclusion = str(run.get("conclusion") or "").lower()
        if status != "completed" or not conclusion:
            skipped += 1
            continue

        run_id = run.get("id")
        workflow = str(
            run.get("name")
            or run.get("workflow_id")
            or "unknown-workflow"
        )
        sha = run.get("head_sha")
        target = f"{workflow}:{run.get('run_number', run_id)}"
        cycle = f"github-actions:{repository}:{run_id}"
        record_ci_result(
            store,
            action_cycle_id=cycle,
            task_target=target,
            strategy_id="github-actions",
            conclusion=conclusion,
            run_id=run_id,
            revision=str(sha) if isinstance(sha, str) else None,
            repository=repository,
            details=f"workflow={workflow} branch={branch}",
        )
        recorded += 1

    return {
        "repository": repository,
        "branch": branch,
        "fetched": len(runs),
        "recorded": recorded,
        "skipped": skipped,
    }
