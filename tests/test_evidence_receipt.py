from automate.dev.evidence import build_receipt, trust_at_least, validate_receipt

def test_evidence_receipt_is_valid_and_records_exact_base():
    receipt = build_receipt(action="autonomous-cycle", repository="rynahmed101-sys/automate",
                            base_sha="a"*40, branch="feat/example", pr_number=123,
                            trust_state="LOCALLY_TESTED",
                            evidence=[{"kind":"focused_tests","status":"passed","reference":"tests/test_example.py"}])
    assert validate_receipt(receipt) == []
    assert receipt["repository"]["base_sha"] == "a"*40
    assert trust_at_least(receipt, "IMPLEMENTED")
    assert not trust_at_least(receipt, "EXACT_HEAD_VERIFIED")

def test_evidence_receipt_rejects_invalid_sha_and_unknown_trust():
    receipt={"schema_version":"automate.evidence_receipt.v1","receipt_id":"rcpt_test123","action":"test",
             "repository":{"full_name":"x/y","base_sha":"bad"},"observed_at":"2026-10-06T00:00:00+00:00",
             "trust_state":"NOT_REAL","evidence":{"items":[]},"unresolved":[]}
    assert validate_receipt(receipt)


def test_receipt_can_bind_action_cycle_and_exact_head():
    receipt = build_receipt(
        action="worker-cycle",
        repository="rynahmed101-sys/automate",
        base_sha="0" * 40,
        trust_state="EXACT_HEAD_VERIFIED",
        evidence=[{"kind": "ci", "status": "passed", "reference": "run:123"}],
        action_cycle_id="cycle_123",
        target="stage1b.improper_integrals",
        packet_id="pkt_123",
        result_id="res_123",
        file_hashes=[{"path": "automate/backend/example.py", "sha256": "a" * 64}],
        verification={"ci_run_ids": [123], "security_run_ids": [124], "tests": ["pytest -q"]},
        final_exact_head_sha="1" * 40,
    )
    assert receipt["action_cycle_id"] == "cycle_123"
    assert receipt["file_hashes"][0]["sha256"] == "a" * 64
    assert receipt["final_exact_head_sha"] == "1" * 40


def test_receipt_preserves_scientific_lineage_and_source_identity():
    from automate.dev.evidence import build_receipt
    receipt = build_receipt(
        action="mirror_experiment",
        repository="rynahmed101-sys/the-mirror",
        base_sha="0123456789abcdef0123456789abcdef01234567",
        trust_state="OBSERVED" if False else "LOCALLY_TESTED",
        evidence=[{"kind": "experiment_observation", "status": "observed", "reference": "exp_123"}],
        capability_id="stage1b.improper_integrals",
        job_id="job_123",
        experiment_id="exp_123",
        run_id="run_123",
        source={
            "provider": "local-mirror",
            "source": "fixture://improper-integrals",
            "retrieved_at": "2026-10-06T00:00:00Z",
            "revision": "fixture-v1",
            "fingerprint": "sha256:example",
            "limitations": ["synthetic fixture"],
        },
    )
    assert receipt["capability_id"] == "stage1b.improper_integrals"
    assert receipt["experiment_id"] == "exp_123"
    assert receipt["source"]["provider"] == "local-mirror"
