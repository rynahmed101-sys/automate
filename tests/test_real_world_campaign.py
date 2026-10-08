            expected,
            parameters={"variable": "x", "order": order},
        )
        report = SymPyChecker().verify_edge(edge, graph)
        assert report.passed, report.error_message
        assert report.status == VerificationStatus.SYMBOLIC_CHECKED
        assert report.details["order"] == order

    graph, edge = _graph_edge(
        "differentiate",
        ["x**3"],
        "4*x**2",
        parameters={"variable": "x", "order": 1},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.status == VerificationStatus.FAILED
    assert not report.passed


def test_campaign_machine_contract_and_capabilities():
    from pathlib import Path

    runner = CliRunner()
    capabilities = runner.invoke(main, ["capabilities", "--json"])
    assert capabilities.exit_code == 0, capabilities.output
    caps = json.loads(capabilities.output)
    assert caps["agent_contract"]["schema_version"] == "automate.agent.v1"
    assert caps["rule_registry"]["count"] == 110

    contract_result = runner.invoke(main, ["schema", "--name", "agent"])
    assert contract_result.exit_code == 0, contract_result.output
    contract = json.loads(contract_result.output)
    assert contract["schema_version"] == "automate.agent.v1"
    assert len(contract["rules"]) == 110
    assert set([
        "discover","parse","context","validate","propose_dry_run","propose_apply",
        "research","check","prove","simulate","stats","query_assumptions",
        "expand","visualize","report","export_certificate","schema","demo"
    ]).issubset(contract["commands"])
    assert Path("schemas/automate-agent-v1.json").exists()