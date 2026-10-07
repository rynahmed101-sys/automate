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
    bootstrap_blockers = [gate for gate in failures if gate != "github_lifecycle_exercised"]
    bootstrap_ready = not bootstrap_blockers and "github_lifecycle_exercised" in failures
    return {
        "schema_version": "automate.autonomy_readiness.v1",
        "ready": not failures,
        "bootstrap_ready": bootstrap_ready,
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


def _foundation_present_on_main(repository: str) -> bool:
    """Require the autonomous foundation to actually exist on live main.

    A PR number is bookkeeping, not authority. A stale/open PR must not block
    readiness when the required foundation is already present on main, and an
    apparently merged PR must not satisfy the gate if its required files are
    absent from main.
    """
    required_files = (
        "automate/dev/autonomous.py",
        "automate/dev/readiness.py",
        "automate/dev/worker_client.py",
        "automate/dev/executor.py",
        "automate/dev/publisher.py",
        "schemas/automate-worker-v1.json",
        "schemas/automate-worker-result-v1.json",
    )
    return all(_github_content_exists(repository, path, "main") for path in required_files)


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

    evidence["autonomous_foundation_merged_main"] = bool(
        _foundation_present_on_main(repository)
    )

    evidence["live_control_plane_clean"] = False
    try:
        live = summarize_live(repository)
        evidence["live_control_plane_clean"] = live.get("valid") is True
        if not evidence["live_control_plane_clean"]:
            errors.extend(list(live.get("errors", [])))
    except Exception as exc:
        errors.append(f"live audit failed: {exc}")

    independent_test_groups = {
        "worker_contract_tested": [
            "tests/test_worker_contract.py",
            "tests/test_worker_client.py",
        ],
        "worker_output_independently_validated": [
            "tests/test_worker_apply.py",
            "tests/test_worker_executor.py",
            "tests/test_worker_publisher.py",
            "tests/test_worker_prmgr.py",
        ],
        "end_to_end_dry_run_passed": [
            "tests/test_autonomous_cycle.py",
            "tests/test_worker_dry_run.py",
            "tests/test_autonomy_readiness.py",
        ],
    }
    for gate, targets in independent_test_groups.items():
        command = [sys.executable, "-m", "pytest", "-q", *targets]
        try:
            completed = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            evidence[gate] = completed.returncode == 0
            if completed.returncode != 0:
                errors.append(f"{gate} evidence suite failed")
        except (OSError, subprocess.SubprocessError) as exc:
            evidence[gate] = False
            errors.append(f"{gate} evidence could not be collected: {exc}")

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
        # Worker repository health is not proof that Automate exercised its own
        # worker -> proposal -> branch -> PR lifecycle.
        evidence["github_lifecycle_exercised"] = False
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
