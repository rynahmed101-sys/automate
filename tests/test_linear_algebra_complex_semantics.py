"""Acceptance tests for Stage 1A complex linear-algebra semantics."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output, *, parameters=None):
    graph = DerivationGraph(id=f"complex_{rule}")
    input_ids = []
    for i, expression in enumerate(inputs):
        node_id = f"in_{i}"
        input_ids.append(node_id)
        graph.add_node(DerivationNode(id=node_id, expression=MathematicalExpression(raw_str=expression)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    graph.add_edge(DerivationEdge(
        id="edge", input_nodes=input_ids, output_nodes=["out"], transformation_rule=rule,
        justification="complex linear-algebra acceptance", checker="linear_algebra", parameters=parameters or {},
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_conjugate_transpose_complex_matrix():
    report = _check(
        "matrix_conjugate_transpose",
        ["Matrix([[1+I, 2], [3*I, 4-I]])"],
        "Matrix([[1-I, -3*I], [2, 4+I]])",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_conjugate_transpose_real_matrix_matches_transpose():
    report = _check(
        "matrix_conjugate_transpose",
        ["Matrix([[1, 2, 3], [4, 5, 6]])"],
        "Matrix([[1, 4], [2, 5], [3, 6]])",
    )
    assert report.passed


def test_unitary_complex_matrix():
    report = _check(
        "matrix_unitary",
        ["Matrix([[1/sqrt(2), I/sqrt(2)], [I/sqrt(2), 1/sqrt(2)]])"],
        "1",
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["passed"] is True


def test_nonunitary_matrix_rejected():
    report = _check("matrix_unitary", ["Matrix([[1, 1], [0, 1]])"], "1")
    assert not report.passed


def test_unitary_symbolic_uncertainty_fails_closed():
    report = _check("matrix_unitary", ["Matrix([[a, 0], [0, 1]])"], "1")
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


def test_unitary_requires_square_matrix():
    report = _check("matrix_unitary", ["Matrix([[1, 0, 0], [0, 1, 0]])"], "1")
    assert not report.passed
    assert "square" in (report.error_message or "").lower()


def test_wrong_conjugate_transpose_and_unitary_claims_rejected():
    assert not _check(
        "matrix_conjugate_transpose",
        ["Matrix([[I, 2], [3, 4]])"],
        "Matrix([[I, 3], [2, 4]])",
    ).passed
    assert not _check(
        "matrix_unitary",
        ["Matrix([[1, 0], [0, 2]])"],
        "1",
    ).passed


def test_registry_exposes_complex_semantics():
    from automate.theory.rules import RuleRegistry
    rules = set(RuleRegistry().list_rule_ids())
    assert {"matrix_conjugate_transpose", "matrix_unitary"}.issubset(rules)
