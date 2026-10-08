from automate.dev.research import build_mirror_mission_job

def test_build_mirror_mission_job_is_bounded_and_exact_revision_scoped():
    sha = "a" * 40
    job = build_mirror_mission_job(
        capability={
            "id":"stage1b.improper_integrals",
            "name":"Improper integrals and convergence-aware handling",
            "task":{"summary":"Investigate convergence tests and singular endpoints","requirements":["cover both tails","avoid principal-value confusion"]},
        },
        source_revision=sha,
        request_id="mis_12345678",
        correlation_id="wrk_12345678",
    )
    assert job["schema_version"] == "mirror.mission_job.v1"
    assert job["execution_kind"] == "mirror_autonomous_mission"
    assert job["target"]["repository"] == "rynahmed101-sys/the-mirror"
    assert job["target"]["workflow"] == "autonomous-mission.yml"
    assert job["source_revision"] == sha
    assert job["limits"]["max_response_bytes"] <= 1_500_000
    assert job["provenance"]["capability_id"] == "stage1b.improper_integrals"
