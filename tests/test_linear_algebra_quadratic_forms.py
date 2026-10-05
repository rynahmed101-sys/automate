"""Stage 1A acceptance campaign for general quadratic forms."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(inputs, output, *, parameters=None):
    graph = DerivationGraph(id="quadratic_form_acceptance")
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
        transformation_rule="quadratic_form_evaluate",
        justification="Stage 1A quadratic-form acceptance",
        checker="linear_algebra",
        parameters=parameters or {},
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_real_quadratic_form():
    report = _check(
        ["Matrix([[2, 1], [1, 3]])", "Vector([2, -1])"],
        "7",
        parameters={"domain": "real"},
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_complex_hermitian_quadratic_form_uses_conjugate_transpose():
    report = _check(
        ["Matrix([[2, I], [-I, 3]])", "Vector([1 + I, 2])"],
        "20",
        parameters={"domain": "complex", "require_hermitian": True},
    )
    assert report.passed


def test_complex_nonhermitian_form_is_still_a_valid_evaluation():
    report = _check(
        ["Matrix([[1, I], [0, 2]])", "Vector([1 + I, 1])"],
        "5 + I",
        parameters={"domain": "complex"},
    )
    assert report.passed


def test_real_non_symmetric_matrix_is_not_silently_symmetrized():
    report = _check(
        ["Matrix([[1, 2], [0, 3]])", "Vector([1, 1])"],
        "6",
        parameters={"domain": "real"},
    )
    assert report.passed
    # The evaluator uses the supplied A directly; no symmetric-part rewrite occurs.


def test_hermitian_requirement_rejects_nonhermitian_matrix():
    report = _check(
        ["Matrix([[1, I], [I, 2]])", "Vector([1, 1])"],
        "2 + 2*I",
        parameters={"domain": "complex", "require_hermitian": True},
    )
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_symbolic_hermitian_requirement_fails_closed():
    report = _check(
        ["Matrix([[a, b], [conjugate(b), a]])", "Vector([1, 2])"],
        "a + 2*b + 2*conjugate(b) + 4*a",
        parameters={"domain": "complex", "require_hermitian": True},
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED


def test_zero_vector_and_zero_matrix():
    zero_vector = _check(
        ["Matrix([[2, 1], [1, 3]])", "Vector([0, 0])"],
        "0",
        parameters={"domain": "real"},
    )
    zero_matrix = _check(
        ["Matrix([[0, 0], [0, 0]])", "Vector([4, -2])"],
        "0",
        parameters={"domain": "real"},
    )
    assert zero_vector.passed and zero_matrix.passed


def test_rank_deficient_matrix():
    report = _check(
        ["Matrix([[1, 1], [1, 1]])", "Vector([2, -2])"],
        "0",
        parameters={"domain": "real"},
    )
    assert report.passed


def test_dimension_and_shape_rejections():
    nonsquare = _check(
        ["Matrix([[1, 2, 3], [4, 5, 6]])", "Vector([1, 2])"],
        "0",
        parameters={"domain": "real"},
    )
    mismatch = _check(
        ["Matrix([[1, 0], [0, 1]])", "Vector([1, 2, 3])"],
        "0",
        parameters={"domain": "real"},
    )
    malformed = _check(
        ["Vector([1, 2])", "Vector([1, 2])"],
        "5",
        parameters={"domain": "real"},
    )
    assert not nonsquare.passed
    assert not mismatch.passed
    assert not malformed.passed


def test_wrong_claim_is_rejected():
    report = _check(
        ["Matrix([[2, 0], [0, 3]])", "Vector([2, 1])"],
        "10",
        parameters={"domain": "real"},
    )
    assert not report.passed


def test_symbolic_evaluation_remains_exact():
    report = _check(
        ["Matrix([[a, b], [b, c]])", "Vector([x, y])"],
        "a*x**2 + 2*b*x*y + c*y**2",
        parameters={"domain": "real"},
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["available"] is False


def test_unsupported_domain_fails_closed():
    report = _check(
        ["Matrix([[1]])", "Vector([2])"],
        "4",
        parameters={"domain": "quaternion"},
    )
    assert not report.passed


def test_registry_exposes_quadratic_form():
    from automate.theory.rules import RuleRegistry

    rule = RuleRegistry().get("quadratic_form_evaluate")
    assert rule is not None
    assert rule.implementation_backend == "linear_algebra"
    assert rule.allowed_checkers == ["linear_algebra"]
