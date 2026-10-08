from automate.dev.promotion_gate import evaluate_promotion

def test_promotion_gate_rejects_evidence_without_main_and_security():
    packet = {
        "authority": "EVIDENCE_ONLY",
        "exact_commit_sha": "a"*40,
        "evidence_state": "PARTIALLY_SUPPORTED",
        "unresolved": ["Security Audit unavailable"],
    }
    state = {
        "main_sha": "b"*40,
        "exact_head_verified": False,
        "security_verified": False,
    }
    decision = evaluate_promotion(
        packet=packet,
        live_state=state,
        pr={"merged": False, "base_sha": "b"*40},
        prior_frontier_clear=False,
    )
    assert decision.allowed is False
    assert any("Security Audit" in reason for reason in decision.reasons)
    assert any("not merged" in reason for reason in decision.reasons)
    assert "security_verified" in decision.required_evidence

def test_promotion_gate_only_allows_fully_bound_candidate():
    sha = "c"*40
    packet = {
        "authority": "EVIDENCE_ONLY",
        "exact_commit_sha": sha,
        "evidence_state": "VERIFIED",
        "unresolved": [],
    }
    state = {"main_sha": sha, "exact_head_verified": True, "security_verified": True}
    decision = evaluate_promotion(
        packet=packet,
        live_state=state,
        pr={"merged": True, "base_sha": sha},
        prior_frontier_clear=True,
    )
    assert decision.allowed is True
    assert decision.reasons == ()
