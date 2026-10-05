"""Phase 1A quadratic-form acceptance campaign."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output):
    graph = DerivationGraph(id=f"quadratic_form_{rule}")
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
            transformation_rule=rule,
            justification="Phase 1A quadratic-form acceptance",
            checker="linear_algebra",
        )
    )
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_quadratic_form_2d_non_symmetric():
    report = _check(
        "quadratic_form",
        ["Vector([2, 3])", "Matrix([[1, 2], [0, 3]])"],
        "43",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["matrix_is_symmetric"] is False
    assert report.details["symmetric_part_equivalent"] is True
    assert report.details["antisymmetric_contribution"] == "0"
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"
    assert report.details["numpy_cross_check"]["engine"] == "numpy.matmul"


def test_quadratic_form_3d_symmetric():
    report = _check(
        "quadratic_form",
        ["Vector([1, -2, 3])", "Matrix([[2, 1, 0], [1, 4, 2], [0, 2, 5]])"],
        "35",
    )
    assert report.passed
    assert report.details["matrix_is_symmetric"] is True


def test_quadratic_form_higher_dimension():
    report = _check(
        "quadratic_form",
        ["Vector([1, 2, -1, 3])", "Matrix([[1, 0, 2, 0], [0, 2, 0, 1], [2, 0, 3, 0], [0, 1, 0, 4]])"],
        "56",
    )
    assert report.passed


def test_quadratic_form_symbolic_exactness():
    report = _check(
        "quadratic_form",
        ["Vector([a, b])", "Matrix([[1, 2], [3, 4]])"],
        "a**2 + 5*a*b + 4*b**2",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["available"] is False


def test_quadratic_form_wrong_claim_fails():
    report = _check(
        "quadratic_form",
        ["Vector([2, 3])", "Matrix([[1, 2], [0, 3]])"],
        "42",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_quadratic_form_shape_mismatch_fails():
    report = _check(
        "quadratic_form",
        ["Vector([1, 2, 3])", "Matrix([[1, 0], [0, 1]])"],
        "5",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_quadratic_form_non_square_matrix_fails():
    report = _check(
        "quadratic_form",
        ["Vector([1, 2])", "Matrix([[1, 2, 3], [4, 5, 6]])"],
        "21",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_quadratic_form_requires_vector_and_matrix():
    report = _check(
        "quadratic_form",
        ["3", "Matrix([[1]])"],
        "9",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_quadratic_form_malformed_matrix_fails_closed():
    report = _check(
        "quadratic_form",
        ["Vector([1, 2])", "Matrix([[1, 2], [3]])"],
        "1",
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_quadratic_form_explicit_complex_semantics_are_unverified():
    report = _check(
        "quadratic_form",
        ["Vector([1, I])", "Matrix([[1, 0], [0, 1]])"],
        "0",
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED
    assert "Complex-valued quadratic forms are unsupported" in report.error_message
