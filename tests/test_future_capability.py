from automate.dev.future_capability import CapabilityAdmissionError, build_future_capability_proposal


def _inputs(status="READY_FOR_INVESTIGATION"):
    proposal = {
        "authority": "UNTRUSTED_RESEARCH_PROPOSAL",
        "status": "CANDIDATE",
        "proposal_id": "proposal_" + "a" * 32,
        "candidate_capability": {
            "id": "future.novel_solver",
            "name": "Novel solver",
            "summary": "A candidate solver discovered during idle exploration.",
            "dependencies": [],
            "prerequisites": [],
        },
    }
    return proposal, {"schema_version": "automate.discovery_triage.v1", "status": status}


def test_future_capability_proposal_is_non_authoritative():
    proposal, triage = _inputs()
    result = build_future_capability_proposal(proposal, triage, suggested_order=9000)
    assert result["authority"] == "UNTRUSTED_FUTURE_CAPABILITY_PROPOSAL"
    assert result["status"] == "CANDIDATE"
    assert result["canonical_ledger_mutated"] is False
    assert result["future_capability_id"].startswith("fcap_")


def test_future_capability_proposal_blocks_nonready_candidate():
    proposal, triage = _inputs("BLOCKED_INCOMPLETE_PREREQUISITES")
    try:
        build_future_capability_proposal(proposal, triage)
    except CapabilityAdmissionError:
        return
    raise AssertionError("blocked candidate must not become an admission proposal")
