"""Core Cartesian vector-calculus identity acceptance campaign."""

from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression
from automate.core.status import VerificationStatus


def _check(rule, field, output, parameters):
    graph = DerivationGraph(id=rule)
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=field)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    edge = DerivationEdge(id="e", input_nodes=["in"], output_nodes=["out"], transformation_rule=rule,
                          justification="Phase 2A identity acceptance", checker="vector_calculus",
                          parameters=parameters)
    return VectorCalculusChecker().verify_edge(edge, graph)


def test_curl_gradient_identity():
    r = _check("curl_gradient_identity", "x**2*y + sin(z)", "0",
               {"coordinates": ["x","y","z"]})
    assert r.passed
    assert r.status == VerificationStatus.SYMBOLIC_CHECKED


def test_divergence_curl_identity():
    r = _check("divergence_curl_identity", "Vector([x*y, y*z, z*x])", "0",
               {"coordinates": ["x","y","z"]})
    assert r.passed


def test_laplacian_identity():
    r = _check("laplacian_identity", "x**2 + y**3 + exp(z)", "0",
               {"coordinates": ["x","y","z"]})
    assert r.passed


def test_identity_wrong_claims_rejected():
    assert not _check("curl_gradient_identity", "x**2*y", "1",
                      {"coordinates": ["x","y","z"]}).passed
    assert not _check("divergence_curl_identity", "Vector([x*y,y*z,z*x])", "1",
                      {"coordinates": ["x","y","z"]}).passed
    assert not _check("laplacian_identity", "x**2+y**2", "1",
                      {"coordinates": ["x","y","z"]}).passed


def test_identity_contracts_fail_closed():
    assert not _check("curl_gradient_identity", "x**2*y", "0", {"coordinates":["x","y"]}).passed
    assert not _check("divergence_curl_identity", "Vector([x,y,z])", "0", {"coordinates":["x","y"]}).passed


def test_identity_registry():
    from automate.theory.rules import RuleRegistry
    assert {"curl_gradient_identity","divergence_curl_identity","laplacian_identity"}.issubset(
        set(RuleRegistry().list_rule_ids())
    )
