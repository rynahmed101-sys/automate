from automate.dev.discovery import triage_candidate


def _proposal(candidate_id="candidate.new.method", deps=None):
    return {
        "schema_version": "mirror.research_proposal.v1",
        "authority": "UNTRUSTED_RESEARCH_PROPOSAL",
        "proposal_id": "proposal_" + "e" * 32,
        "request_id": "research_12345678",
        "capability_id": "stage.discovery",
        "source_revision": "a" * 40,
        "candidate_capability": {
            "id": candidate_id,
            "name": "Candidate",
            "summary": "Candidate discovered method",
            "prerequisites": deps or ["stage1a.linear_algebra"],
            "dependencies": deps or ["stage1a.linear_algebra"],
        },
        "evidence_refs": ["experiment:1"],
        "assumptions": [],
        "risks": ["unverified"],
        "limitations": ["candidate only"],
        "status": "CANDIDATE",
    }


def test_new_candidate_is_non_authoritative_triage():
    result = triage_candidate(_proposal())
    assert result["status"] == "READY_FOR_INVESTIGATION"
    assert result["canonical_inventory_mutated"] is False


def test_unknown_dependency_blocks_candidate():
    result = triage_candidate(_proposal(deps=["candidate.missing.prerequisite"]))
    assert result["status"] == "BLOCKED_UNKNOWN_PREREQUISITES"


def test_existing_id_is_not_silently_replaced():
    result = triage_candidate(_proposal(candidate_id="stage1a.linear_algebra"))
    assert result["status"] == "COLLIDES_WITH_CANONICAL_CAPABILITY"
    assert result["canonical_inventory_mutated"] is False


def test_extract_candidate_proposals_only_accepts_explicit_tool_output():
    from automate.dev.discovery import extract_candidate_proposals

    proposal = _proposal()
    result = extract_candidate_proposals({
        "trace": [
            {"tool": "research_world", "result": {"proposal": proposal}},
            {"tool": "propose_new_capability", "result": {"proposal": proposal}},
        ]
    })
    assert result == [proposal]
