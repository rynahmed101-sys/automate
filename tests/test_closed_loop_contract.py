from automate.dev.learning_runtime import build_learning_handoff
from automate.dev.research import build_mirror_research_job
from automate.dev.triad_probe import run_triad_dry_run
from automate.dev.verification_engine import build_request, mirror_verification_request
from automate.dev.worker import build_worker_packet


def test_closed_loop_role_boundaries_preserve_identity_and_authority():
    revision = "a" * 40
    capability = "stage1b.partial_derivatives"

    worker = build_worker_packet(
        capability,
        repository="rynahmed101-sys/automate",
        base_sha_claim=revision,
        development_branch="engine",
    )
    request = build_request(
        capability_id=capability,
        repository="rynahmed101-sys/automate",
        revision=revision,
        branch="engine",
        scope=["implementation", "verification", "provenance"],
        action_cycle_id="cycle_closed_loop",
    )
    mirror = mirror_verification_request(
        request=request,
        hypothesis="bounded independent mathematical investigation",
        inputs={"revision": revision},
        assumptions=[],
        experiment_budget={"max_runtime_ms": 30000, "max_precision": 80},
    )
    research = build_mirror_research_job(
        capability={"id": capability, "name": capability},
        mirror_endpoint="https://example.invalid/research",
        request_id=worker["packet"]["request_id"],
        correlation_id=request.request_id,
    )
    learning = build_learning_handoff(
        {"experience_id": "exp_" + "b" * 32},
        artifact_type="learning_experience",
        request_id="learning_" + "c" * 32,
        correlation_id=request.action_cycle_id,
        source_revision=revision,
    )

    assert worker["packet"]["request_id"] == research["request_id"]
    assert request.request_id == mirror["request_id"]
    assert mirror["source_revision"] == revision
    assert research["provenance"]["capability_id"] == capability
    assert learning["authority"] == "UNTRUSTED_LEARNING_EVIDENCE"
    assert "authority" not in request.to_dict()
    assert "authority" not in research


def test_existing_triad_dry_run_remains_non_mutating():
    result = run_triad_dry_run(
        "stage1b.partial_derivatives",
        repository="rynahmed101-sys/automate",
        revision="a" * 40,
        branch="engine",
    )
    assert result["status"] == "PASS"
    assert result["mutations_performed"] is False
    assert result["authority_minted"] is False
