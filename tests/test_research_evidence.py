from automate.dev.research import build_evidence_packet, content_sha256, validate_evidence

def test_research_evidence_requires_provenance():
    digest=content_sha256("verified fragment")
    packet=build_evidence_packet(
        request_id="research_test",
        sources=[{
            "source_type":"web","locator":"https://example.invalid/source","title":"Example source",
            "content_sha256":digest,"retrieved_at":"2026-10-06T00:00:00+00:00",
            "query":"test","claim":"example claim"
        }],
    )
    assert validate_evidence(packet)==[]

def test_research_evidence_rejects_unhashed_source():
    packet={"schema_version":"automate.research_evidence.v1","request_id":"x","sources":[{
        "source_type":"web","locator":"https://example.invalid","title":"bad",
        "content_sha256":"not-a-sha","retrieved_at":"now"}]}
    assert validate_evidence(packet)
