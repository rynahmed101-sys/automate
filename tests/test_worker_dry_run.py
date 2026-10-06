"""End-to-end dry run of the bounded worker pipeline."""

import subprocess
from pathlib import Path

from automate.dev.publisher import build_worker_commit


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_build_worker_commit_completes_without_push(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "automate/backend").mkdir(parents=True)
    (repo / "automate/__init__.py").write_text("", encoding="utf-8")
    (repo / "automate/backend/__init__.py").write_text("", encoding="utf-8")
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Automate Test")
    (repo / "README.md").write_text("baseline\\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "baseline")
    base_sha = git(repo, "rev-parse", "HEAD")

    packet = {
        "schema_version": "automate.worker.v1",
        "packet": {
            "request_id": "wrk_test_dryrun",
            "repository": {
                "full_name": "test/automate",
                "base_branch": "main",
                "base_sha_claim": base_sha,
            },
            "capability": {
                "id": "stage1b.dry_run",
                "stage": "1B",
                "name": "Dry-run worker capability",
                "dependencies": [],
            },
            "constraints": {
                "allowed_path_prefixes": [
                    "automate/backend/dry_run.py",
                    "tests/test_dry_run_generated.py",
                    "docs/capabilities/dry_run.md",
                ],
                "forbidden_paths": [],
                "branch_prefix": "feat/",
                "max_files": 3,
                "allow_delete": False,
            },
            "context": {"files": [], "notes": []},
            "instructions": ["Implement only the assigned capability."],
            "verification": {
                "must_run_tests": True,
                "must_report_unresolved": True,
                "must_not_claim_certification": True,
                "test_targets": ["tests/test_dry_run_generated.py"],
            },
        },
    }
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_dryrun",
        "status": "proposed",
        "changes": [
            {
                "operation": "create",
                "path": "automate/backend/dry_run.py",
                "expected_sha": None,
                "content": "VALUE = 1\n",
            },
            {
                "operation": "create",
                "path": "tests/test_dry_run_generated.py",
                "expected_sha": None,
                "content": "def test_generated_value():\n    from automate.backend.dry_run import VALUE\n    assert VALUE == 1\n",
            },
            {
                "operation": "create",
                "path": "docs/capabilities/dry_run.md",
                "expected_sha": None,
                "content": "# Dry run\\n",
            },
        ],
        "tests": [],
        "unresolved": [],
    }

    outcome = build_worker_commit(
        packet["packet"],
        result,
        repository_root=repo,
        commit_message="test: dry-run worker capability",
        enforce_inventory_scope=False,
    )

    assert outcome["status"] == "committed"
    assert outcome["branch"] == "feat/stage1b.dry_run"
    assert len(outcome["commit_sha"]) == 40
    assert outcome["tests"]["authoritative"] is True
    assert git(repo, "branch", "--list", "feat/stage1b.dry_run")
