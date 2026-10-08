from automate.dev import readiness


def test_lifecycle_gate_rejects_forged_request_identity(monkeypatch):
    branch_base_sha = "a" * 40
    claimed_base_sha = "b" * 40
    payload = [{
        "merged_at": "2026-10-07T00:00:00Z",
        "merge_commit_sha": "c" * 40,
        "head": {"ref": "feat/stage1b.series_expansions-" + branch_base_sha[:12]},
        "body": (
            "- capability: stage1b.series_expansions\n"
            "- worker_request_id: wrk_" + "d" * 32 + "\n"
            "- base_sha: " + claimed_base_sha
        ),
    }]
    monkeypatch.setattr(readiness, "_gh_json", lambda *args: payload)
    monkeypatch.setattr(readiness, "_workflow_success", lambda *args: True)
    assert readiness._github_lifecycle_exercised("owner/repo") is False


def test_lifecycle_gate_accepts_deterministic_worker_identity(monkeypatch):
    import hashlib
    import json

    base_sha = "a" * 40
    expected = "wrk_" + hashlib.sha256(
        json.dumps(
            {
                "repository": "owner/repo",
                "base_sha": base_sha,
                "capability_id": "stage1b.series_expansions",
                "development_branch": "main",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()[:32]
    payload = [{
        "merged_at": "2026-10-07T00:00:00Z",
        "merge_commit_sha": "b" * 40,
        "head": {"ref": "feat/stage1b.series_expansions-" + base_sha[:12]},
        "body": (
            "- capability: stage1b.series_expansions\n"
            f"- worker_request_id: {expected}\n"
            f"- base_sha: {base_sha}"
        ),
    }]
    monkeypatch.setattr(readiness, "_gh_json", lambda *args: payload)
    monkeypatch.setattr(readiness, "_workflow_success", lambda *args: True)
    assert readiness._github_lifecycle_exercised("owner/repo") is True
