from automate.dev.research import build_evidence_packet, build_request, content_sha256, validate_evidence, validate_request

def test_research_request_is_bounded():
    request = build_request(request_id="research_test", objective="verify a claim",
                            sources=["web", "paper", "github"], max_sources=5,
                            max_bytes=100000, timeout_ms=10000, query="claim")
    assert validate_request(request) == []

def test_research_request_rejects_unbounded_timeout():
    request = {"schema_version":"automate.research_request.v1","request_id":"x","objective":"x",
               "sources":["web"],"limits":{"max_sources":1,"max_bytes":1024,"timeout_ms":9999999},
               "query":None,"required_evidence":[]}
    assert validate_request(request)

def test_research_evidence_requires_provenance():
    digest = content_sha256("verified fragment")
    packet = build_evidence_packet(request_id="research_test", sources=[{
        "source_type":"web","locator":"https://example.invalid/source","title":"Example source",
        "content_sha256":digest,"retrieved_at":"2026-10-06T00:00:00+00:00",
        "query":"test","claim":"example claim"}])
    assert validate_evidence(packet) == []
