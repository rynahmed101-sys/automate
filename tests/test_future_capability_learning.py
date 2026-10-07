from automate.dev.future_capability_learning import build_future_capability_handoff


def _proposal():
    return {
        "schema_version": "automate.future_capability_proposal.v1",
        "proposal_id": "proposal_test1234",
        "future_capability_id": "fcap_" + "a" * 32,
        "candidate_capability": {
            "id": "candidate.new",
            "name": "Candidate",
            "summary": "Candidate summary",
            "dependencies": [],
            "prerequisites": [],
        },
        "triage": {"status": "READY_FOR_INVESTIGATION"},
        "suggested_stage": "DISCOVERY",
        "suggested_order": None,
        "required_next_steps": ["bounded scientific investigation"],
        "authority": "UNTRUSTED_FUTURE_CAPABILITY_PROPOSAL",
        "canonical_ledger_mutated": False,
        "status": "CANDIDATE",
    }


def test_future_capability_handoff_is_untrusted_and_deterministic():
    first = build_future_capability_handoff(
        _proposal(),
        source_revision="a" * 40,
        correlation_id="ctrl_test1234",
    )
    second = build_future_capability_handoff(
        _proposal(),
        source_revision="a" * 40,
        correlation_id="ctrl_test1234",
    )
    assert first["authority"] == "UNTRUSTED_LEARNING_EVIDENCE"
    assert first["request_id"] == second["request_id"]
    assert first["artifact"]["authority"] == "UNTRUSTED_FUTURE_CAPABILITY_PROPOSAL"
    assert first["artifact"]["canonical_ledger_mutated"] is False
