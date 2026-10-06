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
