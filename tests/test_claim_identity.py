"""Tests for canonical claim identity, dependency hashing, and certificate staleness."""

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.claim import (
    build_claim_identity,
    build_dependency_fingerprint,
    compute_evidence_fingerprint,
)
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.assumptions import Assumption


class DummyChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> str:
        return "1.0"

    def verify_edge(self, edge, graph):
        return VerificationReport(
            status=VerificationStatus.SYMBOLIC_CHECKED,
            backend=self.name,
            backend_version=self.version,
            passed=True,
            details={"execution_config": {"rtol": 1e-8}},
        )


def _graph():
    graph = DerivationGraph(id="claim_test")
    graph.add_node(
        DerivationNode(
            id="root",
            expression=MathematicalExpression(raw_str="x + 1"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="out",
            expression=MathematicalExpression(raw_str="(x + 1)"),
        )
    )
    graph.add_node(
        DerivationNode(
            id="unrelated",
            expression=MathematicalExpression(raw_str="q"),
        )
    )
    graph.add_assumption(
        Assumption(
            id="asm_real",
            description="x is real",
            category="domain_restriction",
            formal_predicate="x ∈ ℝ",
            active=True,
        )
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=["root"],
        output_nodes=["out"],
        transformation_rule="identity_claim",
        justification="Candidate law",
        checker="dummy",
        side_conditions=["asm_real"],
    )
    graph.add_edge(edge)
    return graph, edge


def test_formatting_only_changes_do_not_change_claim_identity():
    graph, edge = _graph()
    first = build_claim_identity(graph, edge).claim_fingerprint_sha256

    graph.nodes["out"].expression.raw_str = " x + 1 "
    second = build_claim_identity(graph, edge).claim_fingerprint_sha256

    assert first == second


def test_semantic_coefficient_change_changes_claim_identity():
    graph, edge = _graph()
    first = build_claim_identity(graph, edge).claim_fingerprint_sha256

    graph.nodes["out"].expression.raw_str = "x + 2"
    second = build_claim_identity(graph, edge).claim_fingerprint_sha256

    assert first != second


def test_unrelated_node_does_not_change_dependency_fingerprint():
    graph, edge = _graph()
    first = build_dependency_fingerprint(graph, edge)

    graph.nodes["unrelated"].expression.raw_str = "q + 999"
    second = build_dependency_fingerprint(graph, edge)

    assert first == second


def test_upstream_change_changes_dependency_fingerprint_and_stales_certificate():
    graph, edge = _graph()
    report = DummyChecker().verify_edge(edge, graph)
    graph.record_verification_report(edge.id, report)

    assert graph.is_certificate_current(edge.id) is True

    graph.nodes["root"].expression.raw_str = "x + 2"

    state = graph.get_certificate_staleness(edge.id)
    assert state["current"] is False
    assert state["reason"] == "CLAIM_CHANGED"


def test_upstream_route_change_changes_dependency_fingerprint():
    graph, edge = _graph()
    parent = graph.get_node("root")
    graph.add_node(
        DerivationNode(
            id="source",
            expression=MathematicalExpression(raw_str="x"),
        )
    )
    graph.add_edge(
        DerivationEdge(
            id="upstream",
            input_nodes=["source"],
            output_nodes=["root"],
            transformation_rule="candidate_relation",
            justification="Exploratory upstream step",
            checker="dummy",
        )
    )

    first = build_dependency_fingerprint(graph, edge)
    graph.edges["upstream"].transformation_rule = "candidate_relation_v2"
    second = build_dependency_fingerprint(graph, edge)

    assert first != second


def test_assumption_change_stales_certificate():
    graph, edge = _graph()
    report = DummyChecker().verify_edge(edge, graph)
    graph.record_verification_report(edge.id, report)
    assert graph.is_certificate_current(edge.id) is True

    graph.assumptions["asm_real"].active = False

    state = graph.get_certificate_staleness(edge.id)
    assert state["current"] is False
    assert state["reason"] in {"CLAIM_CHANGED", "UPSTREAM_DEPENDENCY_CHANGED"}


def test_backend_configuration_changes_evidence_not_claim():
    graph, edge = _graph()

    first_identity = build_claim_identity(graph, edge).claim_fingerprint_sha256
    first_evidence = compute_evidence_fingerprint(
        {"details": {"execution_config": {"rtol": 1e-8}}}
    )
    second_evidence = compute_evidence_fingerprint(
        {"details": {"execution_config": {"rtol": 1e-10}}}
    )

    assert first_identity == build_claim_identity(graph, edge).claim_fingerprint_sha256
    assert first_evidence != second_evidence


def test_all_basechecker_backends_receive_common_identity_stamps():
    graph, edge = _graph()

    report = DummyChecker().verify_edge(edge, graph)

    assert report.claim_fingerprint_sha256
    assert report.dependency_fingerprint_sha256
    assert report.evidence_fingerprint_sha256
    assert report.claim_identity["claim_fingerprint_sha256"] == report.claim_fingerprint_sha256
    assert report.details["claim_fingerprint_sha256"] == report.claim_fingerprint_sha256


def test_serialized_graph_reproduces_same_claim_and_dependency_hashes():
    graph, edge = _graph()
    claim_before = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    dependency_before = graph.get_dependency_fingerprint(edge.id)

    restored = DerivationGraph.from_json(graph.to_json())
    assert restored.get_claim_identity(edge.id).claim_fingerprint_sha256 == claim_before
    assert restored.get_dependency_fingerprint(edge.id) == dependency_before


def test_legacy_certificate_is_explicitly_unknown_not_current():
    graph, edge = _graph()
    from automate.core.edge import DerivationCertificate

    edge.certificate = DerivationCertificate(rule_name=edge.transformation_rule)
    state = graph.get_certificate_staleness(edge.id)

    assert state["current"] is None
    assert state["reason"] == "LEGACY_CERTIFICATE_WITHOUT_IDENTITY"
