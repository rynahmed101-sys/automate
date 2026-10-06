from automate.dev.readiness_evidence import classify_local_evidence, evidence_independence

def test_local_readiness_gates_are_independent():
    result = classify_local_evidence(contract_passed=True, proposal_validation_passed=False, dry_run_passed=True)
    assert result["worker_contract_tested"] is True
    assert result["worker_output_independently_validated"] is False
    assert result["end_to_end_dry_run_passed"] is True

def test_independence_requires_distinct_evidence_records():
    evidence = {"independent_evidence": {
        "worker_contract_tested": {"status": "passed", "reference": "contract"},
        "worker_output_independently_validated": {"status": "passed", "reference": "proposal"},
        "end_to_end_dry_run_passed": {"status": "passed", "reference": "dry-run"},
    }}
    assert evidence_independence(evidence)
    evidence["independent_evidence"]["worker_output_independently_validated"]["reference"] = ""
    assert not evidence_independence(evidence)
