from automate.dev.discovery_job import build_discovery_job


def _grant():
    return {
        "schema_version": "automate.mirror_discovery_grant.v1",
        "grant_id": "dgrant_" + "a" * 32,
        "authority": "UNTRUSTED_EXPLORATION_PERMISSION",
        "issuer": "automate",
        "correlation_id": "ctrl_test1234",
        "issued_at": "2026-10-07T09:00:00.000Z",
        "expires_at": "2026-10-07T09:15:00.000Z",
        "max_candidates": 1,
        "allowed_actions": ["research_world", "propose_new_capability"],
        "forbidden_actions": ["mutate_canonical_inventory", "mutate_phase_ledger"],
        "canonical_mutation_allowed": False,
    }


def test_discovery_job_is_deterministic_and_bounded():
    kwargs = {
        "grant": _grant(),
        "action_cycle_id": "ctrl_test1234",
        "mirror_endpoint": "https://mirror.example/internal/discovery",
    }
    a = build_discovery_job(**kwargs)
    b = build_discovery_job(**kwargs)
    assert a["request_id"] == b["request_id"]
    assert a["request_id"].startswith("djob_")
    assert a["limits"]["max_tool_steps"] <= 8
    assert a["limits"]["max_response_bytes"] <= 1_500_000


def test_discovery_job_rejects_canonical_mutation():
    grant = {**_grant(), "canonical_mutation_allowed": True}
    try:
        build_discovery_job(
            grant=grant,
            action_cycle_id="ctrl_test1234",
            mirror_endpoint="https://mirror.example/internal/discovery",
        )
    except Exception as exc:
        assert "canonical mutation" in str(exc)
    else:
        raise AssertionError("unsafe discovery grant accepted")
