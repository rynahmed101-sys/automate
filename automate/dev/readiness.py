"""Evaluate whether Automate has earned permission to enable autonomous workers."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from automate.dev.live import summarize_live


REQUIRED_GATES = (
    "worker_contract_tested",
    "worker_api_authenticated_bounded",
    "worker_output_independently_validated",
    "github_lifecycle_exercised",
    "live_control_plane_clean",
    "exact_head_authority_current",
    "end_to_end_dry_run_passed",
    "autonomous_foundation_merged_main",
)


def evaluate_readiness(evidence: dict[str, Any]) -> dict[str, Any]:
    failures = [gate for gate in REQUIRED_GATES if evidence.get(gate) is not True]
    return {
        "schema_version": "automate.autonomy_readiness.v1",
        "ready": not failures,
        "gates": {gate: evidence.get(gate) is True for gate in REQUIRED_GATES},
        "blocking_gates": failures,
        "worker_mode": "enabled" if not failures else "off",
        "policy": (
            "Workers may be enabled only when every required gate is true."
            if failures
            else "Autonomous workers are eligible for bounded activation; merge/certification authority remains gated."
        ),
    }


def _gh_json(repository: str, *args: str) -> Any:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required for automatic readiness inspection")
    endpoint = "repos/" + repository
    if args:
        endpoint += "/" + "/".join(arg.strip("/") for arg in args)
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "GitHub query failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub query returned invalid JSON") from exc


def _workflow_success(repository: str, workflow_file: str, commit_sha: str) -> bool:
    env = os.environ.copy()
    if not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        return False
    result = subprocess.run(
        [
            "gh", "run", "list",
            "--repo", repository,
            "--workflow", workflow_file,
            "--commit", commit_sha,
            "--status", "completed",
            "--limit", "20",
            "--json", "databaseId,conclusion",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        return False
    try:
        runs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return any(
        run.get("conclusion") == "success"
        for run in runs
        if isinstance(run, dict)
    )


def _github_content_exists(repository: str, path: str, ref: str) -> bool:
    try:
        _gh_json(repository, f"/contents/{path}?ref={ref}")
        return True
    except Exception:
        return False


def _merged_foundation_pr(repository: str, pr_number: int = 120) -> bool:
    """Require live GitHub merge evidence, never inventory self-report."""
    try:
        pr = _gh_json(repository, f"/pulls/{pr_number}")
    except Exception:
        return False
    return (
        pr.get("number") == pr_number
        and pr.get("base", {}).get("ref") == "main"
        and pr.get("head", {}).get("ref") == "integrate/autonomous-worker-foundation"
        and bool(pr.get("merged_at"))
        and bool(pr.get("merge_commit_sha"))
    )


def collect_readiness_evidence(
    repository: str,
    *,
    worker_repository: str = "rynahmed101-sys/chanfana-openapi-template",
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    errors: list[str] = []

    try:
        ref = _gh_json(repository, "/git/ref/heads/main")
        main_sha = ref.get("object", {}).get("sha")
    except Exception as exc:
        main_sha = None
        errors.append(f"unable to read main SHA: {exc}")

    evidence["exact_head_authority_current"] = bool(
        isinstance(main_sha, str)
        and len(main_sha) == 40
        and _workflow_success(repository, "ci.yml", main_sha)
        and _workflow_success(repository, "security.yml", main_sha)
    )

    required_files = (
        "automate/dev/autonomous.py",
        "automate/dev/readiness.py",
        "automate/dev/worker_client.py",
        "automate/dev/executor.py",
        "automate/dev/publisher.py",
    )
    evidence["autonomous_foundation_merged_main"] = bool(
        _merged_foundation_pr(repository)
        and all(_github_content_exists(repository, path, "main") for path in required_files)
    )

    evidence["live_control_plane_clean"] = False
    try:
        live = summarize_live(repository)
        evidence["live_control_plane_clean"] = live.get("valid") is True
        if not evidence["live_control_plane_clean"]:
            errors.extend(list(live.get("errors", [])))
    except Exception as exc:
        errors.append(f"live audit failed: {exc}")

    local_tests = [
        "tests/test_worker_contract.py",
        "tests/test_worker_apply.py",
        "tests/test_worker_executor.py",
        "tests/test_worker_publisher.py",
        "tests/test_worker_prmgr.py",
        "tests/test_autonomous_cycle.py",
        "tests/test_worker_dry_run.py",
        "tests/test_autonomy_readiness.py",
    ]
    test_command = [sys.executable, "-m", "pytest", "-q", *local_tests]
    try:
        completed = subprocess.run(
            test_command,
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
        passed = completed.returncode == 0
        evidence["worker_contract_tested"] = passed
        evidence["worker_output_independently_validated"] = passed
        evidence["end_to_end_dry_run_passed"] = passed
        if not passed:
            errors.append("autonomous foundation test suite failed")
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"autonomous foundation tests could not run: {exc}")
        evidence["worker_contract_tested"] = False
        evidence["worker_output_independently_validated"] = False
        evidence["end_to_end_dry_run_passed"] = False

    evidence["worker_api_authenticated_bounded"] = False
    evidence["github_lifecycle_exercised"] = False
    try:
        worker_ref = _gh_json(worker_repository, "/git/ref/heads/main")
        worker_sha = worker_ref.get("object", {}).get("sha")
        required_worker_files = (
            "src/worker/auth.ts",
            "src/worker/guard.ts",
            "src/endpoints/worker/jobExecute.ts",
        )
        present = all(
            _github_content_exists(worker_repository, path, "main")
            for path in required_worker_files
        )
        worker_ci = (
            isinstance(worker_sha, str)
            and _workflow_success(worker_repository, "worker-ci.yml", worker_sha)
        )
        evidence["worker_api_authenticated_bounded"] = present and worker_ci
        merged_pr = False
        try:
            closed_prs = _gh_json(
                worker_repository,
                "/pulls?state=closed&base=main&per_page=50",
            )
            merged_pr = any(
                isinstance(pr, dict) and pr.get("merged_at")
                for pr in closed_prs
            )
        except Exception as exc:
            errors.append(f"worker PR lifecycle inspection failed: {exc}")
        evidence["github_lifecycle_exercised"] = present and worker_ci and merged_pr
    except Exception as exc:
        errors.append(f"worker substrate inspection failed: {exc}")

    return {
        "schema_version": "automate.autonomy_readiness.v1",
        "main_sha_observed": main_sha,
        "evidence": evidence,
        "errors": errors,
    }


def auto_readiness(
    repository: str,
    *,
    worker_repository: str = "rynahmed101-sys/chanfana-openapi-template",
) -> dict[str, Any]:
    collected = collect_readiness_evidence(
        repository,
        worker_repository=worker_repository,
    )
    return {**evaluate_readiness(collected["evidence"]), **collected}
