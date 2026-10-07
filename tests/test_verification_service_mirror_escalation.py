from automate.dev import verification_service


def _snapshot(branch="engine"):
    return {
        "repository": "rynahmed101-sys/automate",
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
    }


def _stub_result(kwargs):
    return {
        "evidence_state": "PARTIALLY_SUPPORTED",
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
    }


def _envelope():
    return {
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
        "payload": {"hypothesis": "independent test", "inputs": {"expression": "x"}},
        "provenance": {"parent_ids": [], "requested_by": "automate"},
    }


def test_mirror_escalation_is_opt_in(monkeypatch):
    monkeypatch.setenv("VERIFICATION_ENGINE_JOB_TOKEN", "secret")
    monkeypatch.setenv("VERIFICATION_MIRROR_ESCALATION_ENABLED", "1")
    monkeypatch.setattr(verification_service, "live_repository_snapshot", _snapshot)
    monkeypatch.setattr(verification_service, "run_backlog_item", _stub_result)
    monkeypatch.setattr(
        "automate.dev.mirror_verification_client.run_mirror_verification",
        lambda request: {
            "authority": "UNTRUSTED_EXPERIMENTAL_OBSERVATION",
            "request_id": request["request_id"],
            "source_revision": request["source_revision"],
            "status": "REPRODUCED",
            "experiment_id": "exp_test123",
        },
    )
    status, response = verification_service.verify_payload(_envelope())
    assert status == 200
    assert response["mirror_escalation"]["executed"] is True
    assert response["mirror_observation"]["status"] == "REPRODUCED"


def test_mirror_escalation_is_not_run_by_default(monkeypatch):
    monkeypatch.setenv("VERIFICATION_ENGINE_JOB_TOKEN", "secret")
    monkeypatch.delenv("VERIFICATION_MIRROR_ESCALATION_ENABLED", raising=False)
    monkeypatch.setattr(verification_service, "live_repository_snapshot", _snapshot)
    monkeypatch.setattr(verification_service, "run_backlog_item", _stub_result)
    status, response = verification_service.verify_payload(_envelope())
    assert status == 200
    assert response["mirror_escalation"]["requested"] is True
    assert response["mirror_escalation"]["enabled"] is False
    assert response["mirror_observation"] is None
