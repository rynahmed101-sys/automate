from automate.dev.verification_job import build_verification_job


def test_verification_job_binds_exact_branch_and_revision():
    packet = build_verification_job(
        capability_id="stage1b.series_expansions",
        repository="rynahmed101-sys/automate",
        revision="a" * 40,
        branch="feat/stage1b.series_expansions-" + "b" * 12,
        action_cycle_id="cycle_test123",
        verifier_endpoint="https://automate.example/verification/v1/requests",
    )
    assert packet["request_id"].startswith("ver_")
    assert packet["source_branch"].startswith("feat/stage1b.series_expansions-")
    assert packet["source_revision"] == "a" * 40


def test_verification_job_identity_is_deterministic():
    kwargs = dict(
        capability_id="stage1b.series_expansions",
        repository="rynahmed101-sys/automate",
        revision="a" * 40,
        branch="feat/stage1b.series_expansions-" + "b" * 12,
        action_cycle_id="cycle_test123",
        verifier_endpoint="https://automate.example/verification/v1/requests",
    )
    assert build_verification_job(**kwargs)["request_id"] == build_verification_job(**kwargs)["request_id"]
