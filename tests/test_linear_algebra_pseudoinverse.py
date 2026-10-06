"""Acceptance coverage for Moore-Penrose pseudoinverse and least squares."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output):
    graph = DerivationGraph(id=f"{rule}_acceptance")
    ids=[]
    for i, raw in enumerate(inputs):
        node=f"in_{i}"; ids.append(node)
        graph.add_node(DerivationNode(id=node, expression=MathematicalExpression(raw_str=raw)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    graph.add_edge(DerivationEdge(id="edge", input_nodes=ids, output_nodes=["out"], transformation_rule=rule, justification="Stage 1A acceptance", checker="linear_algebra", parameters={}))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_pseudoinverse_square_invertible():
    report=_check("matrix_pseudoinverse", ["Matrix([[1, 2], [3, 4]])"], "Matrix([[-2, 1], [3/2, -1/2]])")
    assert report.passed, report.error_message
    assert report.details["numpy_cross_check"]["passed"] is True


def test_pseudoinverse_rectangular_rank_deficient():
    report=_check("matrix_pseudoinverse", ["Matrix([[1, 2], [2, 4], [3, 6]])"], "Matrix([[1/70, 1/35, 3/70], [1/35, 2/35, 3/35]])")
    assert report.passed, report.error_message


def test_pseudoinverse_zero_matrix():
    report=_check("matrix_pseudoinverse", ["Matrix([[0, 0], [0, 0]])"], "Matrix([[0, 0], [0, 0]])")
    assert report.passed, report.error_message


def test_pseudoinverse_wrong_claim_rejected():

    report=_check("matrix_pseudoinverse", ["Matrix([[1, 2], [3, 4]])"], "Matrix([[1, 0], [0, 1]])")
    assert not report.passed


def test_least_squares_overdetermined():
    report=_check("linear_least_squares", ["Matrix([[1, 0], [1, 1], [1, 2]])", "Vector([1, 2, 2])"], "Vector([4/3, 1/2])")
    assert report.passed, report.error_message
    assert report.details["numpy_cross_check"]["passed"] is True


def test_least_squares_rank_deficient_returns_minimum_norm_solution():
    report=_check("linear_least_squares", ["Matrix([[1, 1], [2, 2]])", "Vector([1, 2])"], "Vector([1/2, 1/2])")
    assert report.passed


def test_pseudoinverse_rejects_non_moore_penrose_generalized_inverse():
    report=_check("matrix_pseudoinverse", ["Matrix([[1, 0], [0, 0]])"], "Matrix([[1, 0], [1, 0]])")
    assert not report.passed

def test_least_squares_rejects_non_minimum_norm_solution():
    report=_check("linear_least_squares", ["Matrix([[1, 1], [2, 2]])", "Vector([1, 0])"], "Vector([1, 0])")
    assert not report.passed

def test_least_squares_shape_mismatch_rejected():
    report=_check("linear_least_squares", ["Matrix([[1, 0], [0, 1]])", "Matrix([1, 2, 3])"], "Matrix([1, 2])")
    assert not report.passed


def test_symbolic_pseudoinverse_does_not_fake_certainty():
    report=_check("matrix_pseudoinverse", ["Matrix([[a, 0], [0, 1]])"], "Matrix([[1/a, 0], [0, 1]])")
    assert report.status in {VerificationStatus.SYMBOLIC_CHECKED, VerificationStatus.UNVERIFIED}, report.error_message


def test_registry_exposes_both_rules():
    from automate.theory.rules import RuleRegistry
    rules=set(RuleRegistry().list_rule_ids())
    assert {"matrix_pseudoinverse", "linear_least_squares"}.issubset(rules)
