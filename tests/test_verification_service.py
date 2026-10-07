from automate.dev import verification_service as service


def test_service_requires_explicit_token(monkeypatch):
    monkeypatch.delenv("VERIFICATION_ENGINE_JOB_TOKEN", raising=False)
    assert not service._authorized({"Authorization": "Bearer x"})


def test_service_rejects_unbound_revision(monkeypatch):
    monkeypatch.setenv("VERIFICATION_ENGINE_JOB_TOKEN", "secret")
    status, payload = service.verify_payload({
        "action_cycle_id": "cycle_12345678",
        "capability_id": "stage1b.improper_integrals",
        "repository": "rynahmed101-sys/automate",
        "revision": "not-a-sha",
        "branch": "engine",
        "scope": ["mathematical"],
    })
    assert status == 400
    assert "failed closed" in payload["error"]


def test_service_keeps_resource_bounds_explicit():
    assert service.MAX_REQUEST_BYTES == 1_000_000
    assert service.MAX_RESPONSE_BYTES == 1_500_000


def test_verify_payload_accepts_verification_job_envelope(monkeypatch, tmp_path):
    from automate.dev import verification_service

    monkeypatch.setenv("VERIFICATION_ENGINE_JOB_TOKEN", "secret")

    class Snapshot(dict):
        pass

    monkeypatch.setattr(
        verification_service,
        "live_repository_snapshot",
        lambda repository, branch="engine": {
            "repository": repository,
            "main_sha": "1" * 40,
            "engine_sha": "2" * 40,
            "requested_branch": branch,
            "requested_revision": "3" * 40,
            "target_sha": "3" * 40,
            "workflow_runs_main": [],
            "workflow_runs_engine": [],
            "workflow_runs_target": [],
            "combined_status": {},
            "pull_requests": [],
            "compare": {},
            "exact_head_verified": False,
            "security_verified": False,
        },
    )
    monkeypatch.setattr(
        verification_service,
        "run_backlog_item",
        lambda **kwargs: {
            "evidence_state": "BLOCKED",
            "math": [],
            "reconciliation": {"findings": []},
            "packet": {
                "authority": "EVIDENCE_ONLY",
                "action_cycle_id": kwargs["action_cycle_id"],
                "capability_id": kwargs["capability_id"],
                "repository": kwargs["repository"],
                "exact_commit_sha": kwargs["revision"],
                "packet_id": "pkt_test",
                "evidence_graph_ids": [],
                "ci_run_ids": [],
                "security_run_ids": [],
            },
        },
    )
    status, response = verification_service.verify_payload({
        "schema_version": "automate.verification_job.v1",
        "request_id": "ver_" + "a" * 32,
        "action_cycle_id": "cycle_test123",
        "workflow_kind": "mirror_verification",
        "capability_id": "stage1b.series_expansions",
        "source_revision": "3" * 40,
        "source_repository": "rynahmed101-sys/automate",
        "source_branch": "feat/stage1b.series_expansions-" + "b" * 12,
        "verifier_endpoint": "https://automate.example/verification/v1/requests",
        "limits": {"deadline_ms": 30000, "max_response_bytes": 100000},
        "payload": {"purpose": "test"},
        "provenance": {"parent_ids": [], "requested_by": "automate"},
    })
    assert status == 200
    assert response["source_revision"] == "3" * 40
