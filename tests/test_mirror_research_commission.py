from automate.dev.research import build_mirror_research_job

def test_build_mirror_research_job_is_bounded_and_capability_scoped():
    job = build_mirror_research_job(
        capability={
            "id":"stage1b.improper_integrals",
            "name":"Improper integrals and convergence-aware handling",
            "task":{"summary":"Investigate convergence tests and singular endpoints","requirements":["cover both tails","avoid principal-value confusion"]},
        },
        mirror_endpoint="https://mirror.example/api/research/world",
        request_id="res_12345678",
        correlation_id="wrk_12345678",
    )
    assert job["schema_version"] == "mirror.research_job.v1"
    assert job["execution_kind"] == "external_research"
    assert job["research_intent"]["requirements"]
    assert job["limits"]["max_response_bytes"] <= 1_500_000
    assert job["provenance"]["capability_id"] == "stage1b.improper_integrals"
