"""Phase 1A acceptance campaign for linear transformations and matrix representations."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output):
    graph = DerivationGraph(id=f"linear_transform_{rule}")
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(DerivationNode(
            id=node_id,
            expression=MathematicalExpression(raw_str=expression),
        ))
    graph.add_node(DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str=output),
    ))
    graph.add_edge(DerivationEdge(
        id="edge",
        input_nodes=input_ids,
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Phase 1A linear transformation acceptance",
        checker="linear_algebra",
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_rectangular_linear_transformation_application():
    report = _check(
        "linear_transformation_apply",
        ["Matrix([[1, 2, 0], [0, 1, -1]])", "Vector([2, 3, 1])"],
        "Vector([8, 2])",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_linear_transformation_rejects_wrong_output():
    report = _check(
        "linear_transformation_apply",
        ["Matrix([[1, 2], [3, 4]])", "Vector([1, 1])"],
        "Vector([2, 8])",
    )
    assert not report.passed


def test_linear_transformation_rejects_dimension_mismatch():
    report = _check(
        "linear_transformation_apply",
        ["Matrix([[1, 2], [3, 4]])", "Vector([1, 2, 3])"],
        "Vector([1, 2])",
    )
    assert not report.passed


def test_matrix_representation_from_basis_images():
    report = _check(
        "matrix_representation",
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[2, 3], [1, 2]])",
        ],
        "Matrix([[2, 1], [1, 1]])",
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_matrix_representation_rejects_singular_basis():
    report = _check(
        "matrix_representation",
        [
            "Matrix([[1, 2], [2, 4]])",
            "Matrix([[1, 0], [0, 1]])",
        ],
        "Matrix([[1, 0], [0, 1]])",
    )
    assert not report.passed


def test_matrix_representation_symbolic_invertibility_fails_closed():
    report = _check(
        "matrix_representation",
        [
            "Matrix([[a, 0], [0, 1]])",
            "Matrix([[1, 0], [0, 1]])",
        ],
        "Matrix([[1/a, 0], [0, 1]])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED


def test_matrix_representation_rejects_wrong_candidate():
    report = _check(
        "matrix_representation",
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[2, 3], [1, 2]])",
        ],
        "Matrix([[2, 2], [1, 1]])",
    )
    assert not report.passed


def test_unsafe_transformation_input_fails_closed():
    report = _check(
        "linear_transformation_apply",
        ["Matrix([[__import__('os').system('echo pwned')]])", "Vector([1])"],
        "Vector([0])",
    )
    assert not report.passed
