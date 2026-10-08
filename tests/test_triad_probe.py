from automate.dev.triad_probe import TriadProbeError, run_triad_dry_run


def test_triad_dry_run_binds_identity_across_worker_verifier_and_mirror():
    result = run_triad_dry_run(
        "stage1b.partial_derivatives",
        repository="rynahmed101-sys/automate",
        revision="a" * 40,
        branch="engine",
    )
    assert result["status"] == "PASS"
    assert result["mutations_performed"] is False
    assert result["authority_minted"] is False
    assert result["contracts"]["worker_packet"]["packet"]["capability"]["id"] == "stage1b.partial_derivatives"
    assert result["contracts"]["mirror_research_job"]["provenance"]["capability_id"] == "stage1b.partial_derivatives"


def test_triad_dry_run_rejects_malformed_revision():
    try:
        run_triad_dry_run(
            "stage1b.partial_derivatives",
            repository="rynahmed101-sys/automate",
            revision="not-a-sha",
            branch="engine",
        )
    except TriadProbeError as exc:
        assert "40-character commit SHA" in str(exc)
    else:
        raise AssertionError("malformed revision was accepted")


def test_triad_dry_run_rejects_unknown_branch_lane():
    try:
        run_triad_dry_run(
            "stage1b.partial_derivatives",
            repository="rynahmed101-sys/automate",
            revision="a" * 40,
            branch="feature",
        )
    except TriadProbeError as exc:
        assert "main or engine" in str(exc)
    else:
        raise AssertionError("unknown branch lane was accepted")
