"""Acceptance campaign for Phase 1A vector change-of-basis verification."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(inputs, output):
    graph = DerivationGraph(id="change_of_basis")
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(
            DerivationNode(
                id=node_id,
                expression=MathematicalExpression(raw_str=expression),
            )
        )
    graph.add_node(
        DerivationNode(
            id="out",
            expression=MathematicalExpression(raw_str=output),
        )
    )
    graph.add_edge(
        DerivationEdge(
            id="edge",
            input_nodes=input_ids,
            output_nodes=["out"],
            transformation_rule="vector_change_of_basis",
            justification="Phase 1A change-of-basis acceptance",
            checker="linear_algebra",
        )
    )
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_change_of_basis_uses_source_to_target_direction():
    report = _check(
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[1, 0], [1, 1]])",
            "Vector([2, 3])",
        ],
        "Vector([5, -2])",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_change_of_basis_preserves_represented_vector_in_three_dimensions():
    report = _check(
        [
            "Matrix([[1, 1, 0], [0, 1, 1], [0, 0, 1]])",
            "Matrix([[1, 0, 1], [0, 1, 0], [1, 0, 2]])",
            "Vector([2, 3, 4])",
        ],
        "Vector([6, 7, -1])",
    )
    assert report.passed


def test_change_of_basis_identity_target_is_identity_conversion():
    report = _check(
        [
            "Matrix([[2, 0], [0, 3]])",
            "Matrix([[2, 0], [0, 3]])",
            "Vector([4, 5])",
        ],
        "Vector([4, 5])",
    )
    assert report.passed


def test_change_of_basis_rejects_wrong_candidate():
    report = _check(
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[1, 0], [1, 1]])",
            "Vector([2, 3])",
        ],
        "Vector([1, 2])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_change_of_basis_rejects_singular_dependent_basis():
    report = _check(
        [
            "Matrix([[1, 0], [0, 0]])",
            "Matrix([[1, 0], [0, 1]])",
            "Vector([2, 3])",
        ],
        "Vector([2, 3])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_change_of_basis_rejects_basis_dimension_mismatch():
    report = _check(
        [
            "Matrix([[1, 0], [0, 1]])",
            "Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])",
            "Vector([1, 2])",
        ],
        "Vector([1, 2])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_change_of_basis_rejects_coordinate_length_mismatch():
    report = _check(
        [
            "Matrix([[1, 0], [0, 1]])",
            "Matrix([[1, 0], [0, 1]])",
            "Vector([1, 2, 3])",
        ],
        "Vector([1, 2])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_change_of_basis_fails_closed_for_unresolved_symbolic_invertibility():
    report = _check(
        [
            "Matrix([[a, 0], [0, 1]])",
            "Matrix([[1, 0], [0, 1]])",
            "Vector([2, 3])",
        ],
        "Vector([2/a, 3])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED
