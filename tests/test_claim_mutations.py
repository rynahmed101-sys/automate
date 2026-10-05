"""Permanent mutation matrix for canonical claim and certificate identity.

These are deterministic property-style adversarial tests. They intentionally
mutate one semantic input at a time and assert that the verification kernel
does not let a successful certificate survive a changed claim or dependency.
"""

import copy

import pytest

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.claim import build_claim_identity, build_dependency_fingerprint, compute_evidence_fingerprint
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.assumptions import Assumption


pytestmark = [pytest.mark.adversarial, pytest.mark.trust_boundary]


class IdentityChecker(BaseChecker):
    """Minimal backend used only to seed a known-current certificate."""

    @property
    def name(self) -> str:
        return "identity-test"

    @property
    def version(self) -> str:
        return "1"

    def verify_edge(self, edge, graph):
        return VerificationReport(
            status=VerificationStatus.SYMBOLIC_CHECKED,
            backend=self.name,
            backend_version=self.version,
            passed=True,
            details={"test_mode": "mutation-seed"},
        )



def _make_graph() -> tuple[DerivationGraph, DerivationEdge]:
    graph = DerivationGraph(id="mutation_matrix")
    graph.add_node(
        DerivationNode(
            id="source",
            expression=MathematicalExpression(
                raw_str="m * x_ddot + k * x",
                dimension="force",
            ),
            node_kind="equation",
            domain="mechanics",
        )
    )
    graph.add_node(
        DerivationNode(
            id="candidate",
            expression=MathematicalExpression(
                raw_str="0",
                dimension="force",
            ),
            node_kind="equation",
            domain="mechanics",
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
            id="positive_m",
            description="mass is positive",
            category="domain_restriction",
            formal_predicate="m > 0",
            active=True,
        )
    )
    edge = DerivationEdge(
        id="candidate_edge",
        input_nodes=["source"],
        output_nodes=["candidate"],
        transformation_rule="candidate_relation",
        justification="Exploratory candidate relation",
        checker="identity-test",
        parameters={"claim_variant": "baseline"},
        side_conditions=["positive_m"],
    )
    graph.add_edge(edge)
    return graph, edge


def _seed_certificate(graph: DerivationGraph, edge: DerivationEdge):
    report = IdentityChecker().verify_edge(edge, graph)
    graph.record_verification_report(edge.id, report)
    assert graph.is_certificate_current(edge.id) is True
    return report


@pytest.mark.parametrize(
    "mutation_name",
    [
        "coefficient",
        "sign",
        "variable",
        "dimension",
        "domain",
        "node_kind",
        "transformation_rule",
        "semantic_parameter",
        "side_condition",
        "assumption_predicate",
        "assumption_active",
    ],
)
def test_non_equivalent_claim_mutations_change_identity_and_stale_certificate(mutation_name):
    graph, edge = _make_graph()
    _seed_certificate(graph, edge)

    original = graph.get_claim_identity(edge.id).claim_fingerprint_sha256

    if mutation_name == "coefficient":
        graph.nodes["candidate"].expression.raw_str = "1"
    elif mutation_name == "sign":
        graph.nodes["source"].expression.raw_str = "m * x_ddot - k * x"
    elif mutation_name == "variable":
        graph.nodes["source"].expression.raw_str = "m * y_ddot + k * y"
    elif mutation_name == "dimension":
        graph.nodes["candidate"].expression.dimension = "energy"
    elif mutation_name == "domain":
        graph.nodes["source"].domain = "field_theory"
    elif mutation_name == "node_kind":
        graph.nodes["candidate"].node_kind = "scalar"
    elif mutation_name == "transformation_rule":
        edge.transformation_rule = "different_candidate_relation"
    elif mutation_name == "semantic_parameter":
        edge.parameters["claim_variant"] = "mutated"
    elif mutation_name == "side_condition":
        graph.add_assumption(
            Assumption(
                id="different_premise",
                description="different premise",
                category="domain_restriction",
                formal_predicate="m < 0",
                active=True,
            )
        )
        edge.side_conditions = ["different_premise"]
    elif mutation_name == "assumption_predicate":
        graph.assumptions["positive_m"].formal_predicate = "m >= 0"
    elif mutation_name == "assumption_active":
        graph.assumptions["positive_m"].active = False
    else:
        raise AssertionError(f"Unhandled mutation {mutation_name}")

    mutated = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    state = graph.get_certificate_staleness(edge.id)

    assert mutated != original
    assert state["current"] is False
    assert state["reason"] == "CLAIM_CHANGED"
    assert graph.is_certificate_current(edge.id) is False


def test_upstream_dependency_mutation_stales_certificate_without_unrelated_graph_noise():
    graph, edge = _make_graph()
    graph.add_node(
        DerivationNode(
            id="upstream_source",
            expression=MathematicalExpression(raw_str="m * x"),
        )
    )
    upstream = DerivationEdge(
        id="upstream_edge",
        input_nodes=["upstream_source"],
        output_nodes=["source"],
        transformation_rule="derive_source",
        justification="Exploratory upstream derivation",
        checker="identity-test",
    )
    graph.add_edge(upstream)

    _seed_certificate(graph, edge)
    claim_before = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    dependency_before = graph.get_dependency_fingerprint(edge.id)

    graph.nodes["unrelated"].expression.raw_str = "unrelated + 10"
    graph.nodes["upstream_source"].expression.raw_str = "m * x + 1"

    claim_after = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    dependency_after = graph.get_dependency_fingerprint(edge.id)
    state = graph.get_certificate_staleness(edge.id)

    assert claim_after == claim_before
    assert dependency_after != dependency_before
    assert state["reason"] == "UPSTREAM_DEPENDENCY_CHANGED"
    assert state["current"] is False


def test_unrelated_mutations_do_not_stale_successful_certificate():
    graph, edge = _make_graph()
    _seed_certificate(graph, edge)

    claim_before = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    dependency_before = graph.get_dependency_fingerprint(edge.id)

    graph.nodes["unrelated"].expression.raw_str = "unrelated + 10"
    graph.add_node(
        DerivationNode(
            id="another_unrelated",
            expression=MathematicalExpression(raw_str="z"),
        )
    )

    assert graph.get_claim_identity(edge.id).claim_fingerprint_sha256 == claim_before
    assert graph.get_dependency_fingerprint(edge.id) == dependency_before
    assert graph.get_certificate_staleness(edge.id)["current"] is True


def test_evidence_mutation_changes_evidence_identity_without_changing_claim_or_dependency():
    graph, edge = _make_graph()
    report = _seed_certificate(graph, edge)

    claim = graph.get_claim_identity(edge.id).claim_fingerprint_sha256
    dependency = graph.get_dependency_fingerprint(edge.id)

    evidence_one = compute_evidence_fingerprint(
        {"backend": "identity-test", "probe": {"solver_seed": 1}}
    )
    evidence_two = compute_evidence_fingerprint(
        {"backend": "identity-test", "probe": {"solver_seed": 2}}
    )

    assert evidence_one != evidence_two
    assert claim == report.claim_fingerprint_sha256
    assert dependency == report.dependency_fingerprint_sha256
    assert graph.is_certificate_current(edge.id) is True


def test_certificate_identity_cannot_be_manually_relabelled_to_hide_mutation():
    graph, edge = _make_graph()
    _seed_certificate(graph, edge)

    edge.certificate.claim_fingerprint_sha256 = graph.get_claim_identity(
        edge.id
    ).claim_fingerprint_sha256

    graph.nodes["candidate"].expression.raw_str = "1"
    state = graph.get_certificate_staleness(edge.id)

    assert state["current"] is False
    assert state["reason"] == "CLAIM_CHANGED"


def test_mutation_matrix_is_one_field_at_a_time():
    graph, edge = _make_graph()
    original_graph = graph.model_dump()

    mutations = [
        lambda g, e: setattr(g.nodes["candidate"].expression, "raw_str", "1"),
        lambda g, e: setattr(g.nodes["source"].expression, "raw_str", "m * x_ddot - k * x"),
        lambda g, e: setattr(e, "transformation_rule", "mutated_rule"),
        lambda g, e: e.parameters.__setitem__("claim_variant", "mutated"),
    ]

    for mutation in mutations:
        candidate = DerivationGraph.model_validate(copy.deepcopy(original_graph))
        candidate_edge = candidate.get_edge(edge.id)
        before = candidate.get_claim_identity(candidate_edge.id).claim_fingerprint_sha256

        mutation(candidate, candidate_edge)

        after = candidate.get_claim_identity(candidate_edge.id).claim_fingerprint_sha256
        assert after != before
