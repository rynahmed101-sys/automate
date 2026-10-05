"""Phase 1A Linear Algebra subspace, span, and independence acceptance campaign."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.linear_algebra import parse_linear_algebra_expression


def _check(rule, inputs, output, *, parameters=None):
    graph = DerivationGraph(id=f"subspace_{rule}")
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
        justification="Phase 1A subspace acceptance",
        checker="linear_algebra",
        parameters=parameters or {},
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_null_space_basis():
    report = _check(
        "matrix_null_space",
        ["Matrix([[1, 2, 3], [2, 4, 6]])"],
        "Matrix([[-2, -3], [1, 0], [0, 1]])",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_row_space_basis_uses_columns():
    report = _check(
        "matrix_row_space",
        ["Matrix([[1, 2, 3], [2, 4, 6]])"],
        "Matrix([[1], [2], [3]])",
    )
    assert report.passed


def test_column_space_basis():
    report = _check(
        "matrix_column_space",
        ["Matrix([[1, 2, 3], [2, 4, 6]])"],
        "Matrix([[1], [2]])",
    )
    assert report.passed


def test_span_membership():
    inside = _check(
        "vector_span_membership",
        ["Matrix([[1, 0], [0, 1], [0, 0]])", "Vector([2, 3, 0])"],
        "1",
    )
    outside = _check(
        "vector_span_membership",
        ["Matrix([[1, 0], [0, 1], [0, 0]])", "Vector([2, 3, 1])"],
        "0",
    )
    assert inside.passed and outside.passed


def test_linear_independence():
    independent = _check(
        "vector_linear_independence",
        ["Matrix([[1, 0], [0, 1], [0, 0]])"],
        "1",
    )
    dependent = _check(
        "vector_linear_independence",
        ["Matrix([[1, 2], [2, 4], [0, 0]])"],
        "0",
    )
    assert independent.passed and dependent.passed


def test_basis_of_span():
    report = _check(
        "vector_basis_of_span",
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[1, 0], [0, 1]])",
        ],
        "1",
    )
    assert report.passed

    wrong = _check(
        "vector_basis_of_span",
        [
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[1, 2], [0, 0]])",
        ],
        "0",
    )
    assert wrong.passed


def test_zero_dimensional_subspaces():
    null = _check(
        "matrix_null_space",
        ["Matrix([[1, 0], [0, 1]])"],
        "Matrix([[], []])",
    )
    row = _check(
        "matrix_row_space",
        ["Matrix([[0, 0, 0], [0, 0, 0]])"],
        "Matrix([[], [], []])",
    )
    column = _check(
        "matrix_column_space",
        ["Matrix([[0, 0], [0, 0]])"],
        "Matrix([[], []])",
    )
    assert null.passed and row.passed and column.passed


def test_symbolic_subspace_claims_fail_closed():
    report = _check(
        "matrix_null_space",
        ["Matrix([[a, 0], [0, 0]])"],
        "Matrix([[0], [1]])",
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED


def test_negative_and_adversarial_rejections():
    wrong_null = _check(
        "matrix_null_space",
        ["Matrix([[1, 2], [0, 0]])"],
        "Matrix([[1], [0]])",
    )
    assert not wrong_null.passed

    wrong_row_shape = _check(
        "matrix_row_space",
        ["Matrix([[1, 2, 3]])"],
        "Matrix([[1, 2]])",
    )
    assert not wrong_row_shape.passed

    wrong_independence = _check(
        "vector_linear_independence",
        ["Matrix([[1, 2], [2, 4]])"],
        "1",
    )
    assert not wrong_independence.passed

    unsafe = _check(
        "matrix_null_space",
        ["Matrix([[__import__('os').system('echo pwned')]])"],
        "Matrix([[0]])",
    )
    assert not unsafe.passed


def test_zero_column_parser_is_typed_and_safe():
    parsed = parse_linear_algebra_expression("Matrix([[], []])")
    assert parsed.kind == "matrix"
    assert parsed.shape == (2, 0)
