from automate.dev.data import accept_provider_evidence, build_query


def test_data_query_requires_bounded_limits():
    request = build_query(
        request_id="data_1",
        provider="duckdb",
        query="SELECT 1",
        max_rows=10,
        max_bytes=1024,
        timeout_ms=1000,
    )
    assert request["limits"]["max_rows"] == 10


def test_data_evidence_rejects_unbounded_provider_output():
    request = build_query(
        request_id="data_2",
        provider="duckdb",
        query="SELECT * FROM values",
        max_rows=1,
        max_bytes=1024,
    )
    try:
        accept_provider_evidence(
            request,
            {
                "request_id": "data_2",
                "provider": "duckdb",
                "query": request["query"],
                "rows": [{"x": 1}, {"x": 2}],
                "provenance": [],
            },
        )
    except ValueError as exc:
        assert "max_rows" in str(exc)
    else:
        raise AssertionError("unbounded provider output was accepted")


def test_data_evidence_preserves_provenance():
    request = build_query(
        request_id="data_3",
        provider="duckdb",
        query="SELECT 42 AS answer",
    )
    packet = accept_provider_evidence(
        request,
        {
            "request_id": "data_3",
            "provider": "duckdb",
            "query": request["query"],
            "rows": [{"answer": 42}],
            "provenance": [{
                "source_type": "local",
                "locator": "dataset.parquet",
                "retrieved_at": "2026-10-06T12:00:00Z",
                "content_sha256": "a" * 64,
            }],
        },
    )
    assert packet["provenance"][0]["locator"] == "dataset.parquet"
    assert packet["stats"]["row_count"] == 1
