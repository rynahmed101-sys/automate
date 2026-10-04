"""
Graph-claim binding tests for TensorChecker.

A verification backend must not silently replace the graph's metric claim with
a different metric supplied through parameters. The input node is the trusted
claim being verified.
"""

import pytest

from automate.backend.tensor_backend import TensorChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode, MathematicalExpression
from automate.core.status import VerificationStatus


pytestmark = pytest.mark.trust_boundary


def _metric_graph(metric_name: str, named_metric: str) -> tuple[DerivationGraph, DerivationEdge]:
    graph = DerivationGraph(id="tensor_binding_test")
    graph.add_node(DerivationNode(
        id="metric",
        expression=MathematicalExpression(raw_str=metric_name),
        node_kind="expression",
        domain="differential_geometry",
    ))
    graph.add_node(DerivationNode(
        id="claim",
        expression=MathematicalExpression(raw_str="0"),
        node_kind="scalar",
        domain="differential_geometry",
    ))
    edge = DerivationEdge(
        id="edge_ricci_scalar",
        input_nodes=["metric"],
        output_nodes=["claim"],
        transformation_rule="ricci_scalar",
        justification="Test metric claim binding.",
        checker="tensor",
        parameters={"named_metric": named_metric},
    )
    graph.add_edge(edge)
    return graph, edge


def test_conflicting_named_metric_cannot_override_graph_claim():
    graph, edge = _metric_graph("flat_2d", "polar_2d")

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "conflicting named_metric" in (report.error_message or "")


def test_matching_named_metric_remains_verifiable():
    graph, edge = _metric_graph("flat_2d", "flat_2d")

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED


def test_matching_metric_records_claim_fingerprint():
    graph, edge = _metric_graph("flat_2d", "flat_2d")

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is True, report.error_message
    assert len(report.details["claim_fingerprint_sha256"]) == 64
    assert edge.certificate is not None
    assert edge.certificate.metrics["claim_fingerprint_sha256"] == report.details["claim_fingerprint_sha256"]
