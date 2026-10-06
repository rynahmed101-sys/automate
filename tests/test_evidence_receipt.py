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
