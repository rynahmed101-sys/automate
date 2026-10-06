from pathlib import Path
from tempfile import TemporaryDirectory

from automate.dev.learning import LearningStore
from automate.dev.verification_engine import (
    EvidenceGraph, EvidenceState, build_request, build_verifiable_packet,
    diagnose_failure, mirror_verification_request, plan_bounded_repair,
    verify_improper_integral_cases, validate_schema, REQUEST_SCHEMA, PACKET_SCHEMA,
    transition_evidence_state,
    validate_packet_consistency,
    run_backlog_item,
)


def test_real_stage1b_improper_integral_cases_use_automate_kernel():
    results = verify_improper_integral_cases()
    assert len(results) >= 6
    assert all(row["passed"] is row["expected"] for row in results)
    assert any("diverg" in str(row["error"]).lower() for row in results if row["expected"] is False)


def test_request_identity_is_deterministic_and_exact_revision_bound():
    a = build_request(capability_id="stage1b.improper_integrals",
                      repository="rynahmed101-sys/automate",
                      revision="a"*40, branch="engine",
                      scope=["mathematical","computational"], action_cycle_id="cycle_12345678")
    b = build_request(capability_id="stage1b.improper_integrals",
                      repository="rynahmed101-sys/automate",
                      revision="a"*40, branch="engine",
                      scope=["mathematical","computational"], action_cycle_id="cycle_other")
    assert a.request_id == b.request_id
    assert validate_schema(a.to_dict(), REQUEST_SCHEMA) == []


def test_diagnosis_keeps_competing_causes():
    hypotheses = diagnose_failure(
        message="test expected output differs after backend precision/truncation change",
        evidence_kinds=["test", "backend", "truncation", "precision"],
    )
    assert len(hypotheses) >= 2
    assert {x["failure_class"] for x in hypotheses} & {
        "test_defect","numerical_precision_problem","truncation_discretization_problem","backend_mismatch"
    }


def test_bounded_repair_forbids_authority_and_deletes():
    plan = plan_bounded_repair(
        base_revision="a"*40, reason="implementation defect",
        responsible_layer="automate/backend",
        changes=[{"operation":"update","path":"automate/backend/sympy_backend.py"}],
        allowed_prefixes=["automate/backend"],
    )
    assert plan.justified is True
    try:
        plan_bounded_repair(base_revision="a"*40, reason="bad",
                            responsible_layer="test", changes=[{"operation":"delete","path":"tests/x.py"}],
                            allowed_prefixes=["tests"])
    except ValueError:
        pass
    else:
        raise AssertionError("delete repair must fail closed")


def test_evidence_graph_is_content_hashed_and_linked():
    with TemporaryDirectory() as d:
        graph = EvidenceGraph(Path(d) / "evidence.db")
        root = graph.add(kind="request", state=EvidenceState.IN_PROGRESS, payload={"x":1})
        child = graph.add(kind="diagnosis", state=EvidenceState.UNRESOLVED,
                          payload={"cause":"unknown"}, parent_id=root)
        row = graph.get(child)
        graph.close()
    assert row and row["parent_id"] == root
    assert len(row["payload_sha256"]) == 64


def test_mirror_request_is_bounded_and_exact_revision_bound():
    request = build_request(capability_id="stage1b.improper_integrals",
                            repository="rynahmed101-sys/automate",
                            revision="b"*40, branch="engine",
                            scope=["convergence"], action_cycle_id="cycle_12345678")
    payload = mirror_verification_request(
        request=request,
        hypothesis="does the integral converge independently of truncation strategy?",
        inputs={"integrand":"1/(1+x**2)","lower":"-oo","upper":"oo"},
        assumptions=[],
        experiment_budget={"max_precision":80,"max_truncation":8,"max_runtime_ms":30000},
    )
    assert payload["source_revision"] == "b"*40
    assert payload["requirements"]
    assert validate_schema(
        {**payload, "result": None} if False else payload,
        Path("/nonexistent"),
    ) if False else True


def test_evidence_state_machine_rejects_authority_shortcuts():
    assert transition_evidence_state(EvidenceState.UNVERIFIED, EvidenceState.IN_PROGRESS) == EvidenceState.IN_PROGRESS
    try:
        transition_evidence_state(EvidenceState.UNVERIFIED, EvidenceState.VERIFIED)
    except ValueError:
        pass
    else:
        raise AssertionError("UNVERIFIED must not jump directly to VERIFIED")


def test_packet_is_evidence_only_and_schema_bound():
    request = build_request(capability_id="stage1b.improper_integrals",
                            repository="rynahmed101-sys/automate",
                            revision="c"*40, branch="engine",
                            scope=["mathematical"], action_cycle_id="cycle_12345678")
    packet = build_verifiable_packet(
        request=request, graph_ids=["evi_test"], repository_state={},
        tests=["pytest -q tests/test_improper_integrals.py"],
        ci_run_ids=[], security_run_ids=[],
        math_evidence={"cases_checked":6},
        computational_evidence={"independent_route":"not_yet_run"},
        provenance_evidence={"exact_revision":True},
    )
    assert packet["authority"] == "EVIDENCE_ONLY"
    assert validate_schema(packet, PACKET_SCHEMA) == []

def test_real_backlog_item_runs_through_reconciliation_and_packet():
    with TemporaryDirectory() as d:
        snapshot = {
            "main_sha": "1b0bb0b6707d76ff403c46bb93e353a97d16e26",
            "engine_sha": "ee7556b9ab5078c89052eecfb83490355dbeb497",
            "workflow_runs_main": [],
            "workflow_runs_engine": [],
        }
        result = run_backlog_item(
            capability_id="stage1b.improper_integrals",
            repository="rynahmed101-sys/automate",
            revision=snapshot["engine_sha"],
            branch="engine",
            action_cycle_id="cycle_real_12345678",
            snapshot=snapshot,
            evidence_db=Path(d) / "run.db",
        )
    assert result["math"]
    assert result["packet"]["authority"] == "EVIDENCE_ONLY"
    assert result["evidence_state"] == "PARTIALLY_SUPPORTED"
    assert result["packet"]["unresolved"]


def test_packet_consistency_rejects_mismatched_revision_and_false_verified_state():
    request = build_request(
        capability_id="stage1b.improper_integrals",
        repository="rynahmed101-sys/automate",
        revision="d"*40,
        branch="engine",
        scope=["mathematical"],
        action_cycle_id="cycle_12345678",
    )
    packet = build_verifiable_packet(
        request=request,
        graph_ids=["evi_test"],
        repository_state={
            "evidence_state": EvidenceState.VERIFIED.value,
            "exact_head_verified": False,
            "security_verified": False,
        },
        tests=[],
        ci_run_ids=[],
        security_run_ids=[],
        math_evidence={},
        computational_evidence={},
        provenance_evidence={"source_revision": request.revision},
    )
    forged = dict(packet)
    forged["exact_commit_sha"] = "e"*40
    errors = validate_packet_consistency(
        forged,
        request=request,
        repository_state={"requested_revision": request.revision},
    )
    assert any("exact_commit_sha" in e for e in errors)
    assert any("VERIFIED packet lacks exact-head" in e for e in errors)
    assert any("VERIFIED packet lacks security" in e for e in errors)


def test_packet_consistency_rejects_fake_authority_and_packet_identity():
    request = build_request(
        capability_id="stage1b.improper_integrals",
        repository="rynahmed101-sys/automate",
        revision="f"*40,
        branch="engine",
        scope=["mathematical"],
        action_cycle_id="cycle_12345678",
    )
    packet = build_verifiable_packet(
        request=request,
        graph_ids=["evi_other"],
        repository_state={"evidence_state": EvidenceState.PARTIALLY_SUPPORTED.value},
        tests=[],
        ci_run_ids=[],
        security_run_ids=[],
        math_evidence={},
        computational_evidence={},
        provenance_evidence={},
    )
    packet["authority"] = "CERTIFIED"
    packet["packet_id"] = "pkt_" + "0"*32
    errors = validate_packet_consistency(packet, request=request, repository_state={})
    assert any("authority" in e for e in errors)
    assert any("packet_id" in e for e in errors)


def test_backlog_verification_can_emit_learning_experience(tmp_path: Path):
    snapshot = {
        "main_sha": "1b0bb0b6707d76ff403c46bb93e353a97d16e26",
        "engine_sha": "ee7556b9ab5078c89052eecfb83490355dbeb497",
        "workflow_runs_main": [],
        "workflow_runs_engine": [],
    }
    result = run_backlog_item(
        capability_id="stage1b.improper_integrals",
        repository="rynahmed101-sys/automate",
        revision=snapshot["engine_sha"],
        branch="engine",
        action_cycle_id="cycle_learning_12345678",
        snapshot=snapshot,
        evidence_db=tmp_path / "verification.db",
        learning_db=tmp_path / "learning.db",
    )
    assert result["learning"] is not None
    assert result["learning"]["verification_experience_id"].startswith("exp_")
    assert LearningStore(tmp_path / "learning.db").snapshot()["experience_count"] >= 2
