"""Named Phase 1A Linear Algebra Core acceptance campaign."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph(rule, inputs, output, *, parameters=None, checker="linear_algebra"):
    graph = DerivationGraph(id=f"linear_algebra_{rule}")
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(DerivationNode(id=node_id, expression=MathematicalExpression(raw_str=expression)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    graph.add_edge(DerivationEdge(
        id="edge", input_nodes=input_ids, output_nodes=["out"],
        transformation_rule=rule, justification="Phase 1A acceptance",
        checker=checker, parameters=parameters or {},
    ))
    return graph, graph.edges["edge"]


def _check(rule, inputs, output, **kwargs):
    graph, edge = _graph(rule, inputs, output, **kwargs)
    return LinearAlgebraChecker().verify_edge(edge, graph)


def test_vector_core():
    assert _check("vector_add", ["Vector([1, 2, 3])", "Vector([4, 5, 6])"], "Vector([5, 7, 9])").passed
    assert _check("vector_subtract", ["Vector([4, 5, 6])", "Vector([1, 2, 3])"], "Vector([3, 3, 3])").passed
    assert _check("vector_scalar_multiply", ["Vector([1, -2, 3])"], "Vector([2, -4, 6])",
                  parameters={"scalar": "2"}).passed
    report = _check("vector_dot", ["Vector([1, 2, 3])", "Vector([4, 5, 6])"], "32")
    assert report.passed and report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_symbolic_vector_dot():
    report = _check("vector_dot", ["Vector([a, b, c])", "Vector([x, y, z])"], "a*x + b*y + c*z")
    assert report.passed
    assert report.details["numpy_cross_check"]["available"] is False


def test_matrix_core():
    assert _check("matrix_multiply",
                  ["Matrix([[1, 2], [3, 4]])", "Matrix([[5, 6], [7, 8]])"],
                  "Matrix([[19, 22], [43, 50]])").passed
    assert _check("matrix_multiply",
                  ["Matrix([[1, 2, 3], [4, 5, 6]])", "Matrix([[7, 8], [9, 10], [11, 12]])"],
                  "Matrix([[58, 64], [139, 154]])").passed
    assert _check("matrix_transpose", ["Matrix([[1, 2, 3], [4, 5, 6]])"],
                  "Matrix([[1, 4], [2, 5], [3, 6]])").passed
    assert _check("matrix_determinant", ["Matrix([[1, 2], [3, 4]])"], "-2").passed
    assert _check("matrix_trace", ["Matrix([[1, 2], [3, 4]])"], "5").passed


def test_symbolic_determinant():
    report = _check("matrix_determinant", ["Matrix([[a, b], [c, d]])"], "a*d - b*c")
    assert report.passed and report.details["numpy_cross_check"]["available"] is False


def test_inverse_rank_rref():
    assert _check("matrix_inverse", ["Matrix([[4, 7], [2, 6]])"],
                  "Matrix([[3/5, -7/10], [-1/5, 2/5]])").passed
    assert _check("matrix_rank", ["Matrix([[1, 2, 3], [2, 4, 6]])"], "1").passed
    report = _check("matrix_rref", ["Matrix([[1, 2], [2, 4]])"], "Matrix([[1, 2], [0, 0]])")
    assert report.passed and report.certificates


def test_linear_system_solve():
    report = _check("linear_system_solve",
                    ["Matrix([[2, 1], [1, -1]])", "Vector([5, 1])"],
                    "Vector([2, 1])")
    assert report.passed
    assert len(report.certificates) == 3


def test_symbolic_linear_system_solve():
    report = _check("linear_system_solve",
                    ["Matrix([[a, 0], [0, b]])", "Vector([x, y])"],
                    "Vector([x/a, y/b])")
    assert report.passed and report.details["numpy_cross_check"]["available"] is False


def test_composition():
    graph = DerivationGraph(id="linear_algebra_composition")
    for node_id, expression, kind in [
        ("A", "Matrix([[1, 2], [3, 4]])", "matrix"),
        ("At", "Matrix([[1, 3], [2, 4]])", "matrix"),
        ("gram", "Matrix([[10, 14], [14, 20]])", "matrix"),
    ]:
        graph.add_node(DerivationNode(id=node_id, expression=MathematicalExpression(raw_str=expression), node_kind=kind))
    graph.add_edge(DerivationEdge(id="transpose", input_nodes=["A"], output_nodes=["At"],
                                  transformation_rule="matrix_transpose", justification="Composition",
                                  checker="linear_algebra"))
    graph.add_edge(DerivationEdge(id="product", input_nodes=["At", "A"], output_nodes=["gram"],
                                  transformation_rule="matrix_multiply", justification="Composition",
                                  checker="linear_algebra"))
    checker = LinearAlgebraChecker()
    assert checker.verify_edge(graph.edges["transpose"], graph).passed
    assert checker.verify_edge(graph.edges["product"], graph).passed


def test_adversarial_rejections():
    report = _check("vector_add", ["Vector([1, 2, 3])", "Vector([4, 5, 6])"], "Vector([5, 8, 9])")
    assert not report.passed and report.status == VerificationStatus.FAILED

    report = _check("vector_add", ["Vector([1, 2])", "Vector([3, 4, 5])"], "Vector([4, 6])")
    assert not report.passed and "shape mismatch" in (report.error_message or "").lower()

    report = _check("matrix_multiply",
                    ["Matrix([[1, 2, 3], [4, 5, 6]])", "Matrix([[1, 2], [3, 4]])"],
                    "Matrix([[7, 8], [9, 10]])")
    assert not report.passed and "shape mismatch" in (report.error_message or "").lower()

    report = _check("matrix_determinant", ["Matrix([[1, 2, 3], [4, 5, 6]])"], "0")
    assert not report.passed and "square" in (report.error_message or "").lower()

    report = _check("matrix_inverse", ["Matrix([[1, 2], [2, 4]])"], "Matrix([[1, 0], [0, 1]])")
    assert not report.passed and "singular" in (report.error_message or "").lower()

    report = _check("linear_system_solve", ["Matrix([[1, 2], [2, 4]])", "Vector([3, 6])"], "Vector([1, 1])")
    assert not report.passed and "unique solution" in (report.error_message or "").lower()

    report = _check("linear_system_solve", ["Matrix([[1, 1], [1, 1]])", "Vector([1, 2])"], "Vector([0, 0])")
    assert not report.passed


def test_safe_parsing_and_shape_rejections():
    assert not _check("matrix_transpose", ["Matrix([[1, 2], [3]])"], "Matrix([[1, 3], [2, 4]])").passed
    assert not _check("matrix_transpose", ["Matrix(eye(2))"], "Matrix([[1, 0], [0, 1]])").passed
    assert not _check("matrix_rank", ["Matrix([[1, 0], [0, 1]])"], "1").passed


def test_registry_exposes_core_family():
    from automate.theory.rules import RuleRegistry
    expected = {
        "vector_add", "vector_subtract", "vector_scalar_multiply", "vector_dot",
        "matrix_multiply", "matrix_transpose", "matrix_determinant", "matrix_trace",
        "matrix_inverse", "matrix_rank", "matrix_rref", "linear_system_solve",
        "matrix_null_space", "matrix_row_space", "matrix_column_space",
        "vector_span_membership", "vector_linear_independence", "vector_basis_of_span",
    }
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
