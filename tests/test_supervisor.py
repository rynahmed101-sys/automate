        lambda _: {"repository": "x", "valid": True, "errors": []},
    )
    result = supervisor_snapshot(
        "rynahmed101-sys/automate",
        base_sha="0000000000000000000000000000000000000000",
    )
    assert result["action"] == "continue_development"
    assert result["can_dispatch"] is False
    assert result["queue"]["next_action"]["capability_ids"] == ["stage1b.improper_integrals"]
    assert (
        result["worker_packet"]["packet"]["repository"]["base_sha_claim"]
        == "0000000000000000000000000000000000000000"
    )