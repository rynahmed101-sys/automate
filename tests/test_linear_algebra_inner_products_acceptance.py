"""Named Phase 1A Linear Algebra inner-product capability acceptance campaign."""

from automate.ai.proposals import apply_and_verify_proposal
from automate.ai.schemas import DerivationProposal
from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph(rule, inputs, outputs, *, parameters=None):
    graph = DerivationGraph(id=f"linear_algebra_{rule}")
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(
            DerivationNode(id=node_id, expression=MathematicalExpression(raw_str=expression))
        )
    output_ids = []
    for index, expression in enumerate(outputs):
        node_id = f"out_{index}"
        output_ids.append(node_id)
        graph.add_node(
            DerivationNode(id=node_id, expression=MathematicalExpression(raw_str=expression))
        )
    graph.add_edge(
        DerivationEdge(
            id="edge",
            input_nodes=input_ids,
            output_nodes=output_ids,
            transformation_rule=rule,
            justification="Phase 1A inner-product acceptance",
            checker="linear_algebra",
            parameters=parameters or {},
        )
    )
    return graph, graph.edges["edge"]


def _check(rule, inputs, output=None, *, outputs=None, parameters=None):
    graph, edge = _graph(
        rule,
        inputs,
        outputs if outputs is not None else [output],
        parameters=parameters,
    )
    return LinearAlgebraChecker().verify_edge(edge, graph)


def test_vector_norm_exact_and_numeric_cross_check():
    report = _check("vector_norm", ["Vector([3, 4])"], "5")
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_symbolic_and_complex_inner_products():
    report = _check(
        "vector_inner_product",
        ["Vector([a, b])", "Vector([x, y])"],
        "conjugate(a)*x + conjugate(b)*y",
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["available"] is False

    report = _check(
        "vector_inner_product",
        ["Vector([I, 1])", "Vector([I, 1])"],
        "2",
    )
    assert report.passed

    report = _check(
        "vector_inner_product",
        ["Vector([I, 1])", "Vector([I, 1])"],
        "0",
        parameters={"hermitian": False},
    )
    assert report.passed


def test_orthogonality_indicator_and_scaling():
    report = _check("vector_orthogonal", ["Vector([1, 0])", "Vector([0, 7])"], "1")
    assert report.passed
    assert report.details["numpy_cross_check"]["passed"] is True

    report = _check("vector_orthogonal", ["Vector([1, 2])", "Vector([2, 1])"], "0")
    assert report.passed

    report = _check("vector_orthogonal", ["Vector([1, 0])", "Vector([0, 2])"], "1")
    assert report.passed


def test_projection_exact_and_complex():
    report = _check(
        "vector_projection",
        ["Vector([2, 3])", "Vector([1, 0])"],
        "Vector([2, 0])",
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["passed"] is True

    report = _check(
        "vector_projection",
        ["Vector([I, 1])", "Vector([I, 0])"],
        "Vector([I, 0])",
    )
    assert report.passed


def test_gram_schmidt_orthogonal_and_orthonormal():
    report = _check(
        "vector_gram_schmidt",
        ["Vector([1, 1])", "Vector([1, 0])"],
        outputs=["Vector([1, 1])", "Vector([1/2, -1/2])"],
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["passed"] is True
    assert report.details["output_shapes"] == [[2], [2]]

    report = _check(
        "vector_gram_schmidt",
        ["Vector([1, 1])", "Vector([1, 0])"],
        outputs=[
            "Vector([sqrt(2)/2, sqrt(2)/2])",
            "Vector([sqrt(2)/2, -sqrt(2)/2])",
        ],
        parameters={"orthonormal": True},
    )
    assert report.passed
    assert report.details["numpy_cross_check"]["passed"] is True


def test_symbolic_gram_schmidt():
    report = _check(
        "vector_gram_schmidt",
        ["Vector([1, 0])", "Vector([x, 1])"],
        outputs=["Vector([1, 0])", "Vector([0, 1])"],
    )
    assert report.passed


def test_zero_and_degenerate_cases_fail_closed():
    report = _check("vector_projection", ["Vector([1, 2])", "Vector([0, 0])"], "Vector([0, 0])")
    assert not report.passed and "zero vector" in (report.error_message or "").lower()

    report = _check(
        "vector_gram_schmidt",
        ["Vector([1, 2])", "Vector([2, 4])"],
        outputs=["Vector([1, 2])", "Vector([0, 0])"],
    )
    assert not report.passed and "linearly dependent" in (report.error_message or "").lower()

    report = _check(
        "vector_gram_schmidt",
        ["Vector([1, 2])", "Vector([1, 2, 3])"],
        outputs=["Vector([1, 2])", "Vector([1, 2, 3])"],
    )
    assert not report.passed and "same dimension" in (report.error_message or "").lower()


def test_symbolic_unknown_boundaries_return_unverified():
    report = _check(
        "vector_orthogonal",
        ["Vector([x, 0])", "Vector([1, 0])"],
        "1",
    )
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed

    report = _check(
        "vector_projection",
        ["Vector([1, 0])", "Vector([x, 0])"],
        "Vector([1, 0])",
    )
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


def test_adversarial_wrong_results_are_rejected():
    assert not _check("vector_norm", ["Vector([3, 4])"], "4").passed
    assert not _check("vector_inner_product", ["Vector([1, 2])", "Vector([3, 4])"], "10").passed
    assert not _check("vector_orthogonal", ["Vector([1, 0])", "Vector([1, 0])"], "1").passed
    assert not _check(
        "vector_projection",
        ["Vector([2, 3])", "Vector([1, 0])"],
        "Vector([0, 3])",
    ).passed
    assert not _check(
        "vector_gram_schmidt",
        ["Vector([1, 1])", "Vector([1, 0])"],
        outputs=["Vector([1, 1])", "Vector([1, 1])"],
    ).passed


def test_malformed_inputs_and_output_contracts_fail_closed():
    assert not _check("vector_inner_product", ["Vector([1, 2])", "Vector([3])"], "3").passed
    assert not _check("vector_norm", ["Matrix([[1, 2]])"], "sqrt(5)").passed
    assert not _check(
        "vector_gram_schmidt",
        ["Vector([1, 0])", "Vector([0, 1])"],
        outputs=["Vector([1, 0])"],
    ).passed


def test_ai_proposal_path_for_inner_product():
    graph = DerivationGraph(id="ai_linear_algebra_inner_product")
    graph.add_node(
        DerivationNode(
            id="a",
            expression=MathematicalExpression(raw_str="Vector([1, 2])"),
            node_kind="vector",
        )
    )
    graph.add_node(
        DerivationNode(
            id="b",
            expression=MathematicalExpression(raw_str="Vector([3, 4])"),
            node_kind="vector",
        )
    )
    proposal = DerivationProposal(
        proposal_id="la_inner_agent_001",
        input_nodes=["a", "b"],
        output_nodes=[{"id": "dot", "expression": "11", "node_kind": "scalar"}],
        rule="vector_inner_product",
        justification="The Hermitian inner product of two real vectors.",
        target_checker="linear_algebra",
        origin={"type": "ai", "provider": "acceptance"},
    )
    dry = apply_and_verify_proposal(proposal, graph, dry_run=True)
    assert dry.success and not dry.graph_updated and "dot" not in graph.nodes
    applied = apply_and_verify_proposal(proposal, graph, dry_run=False)
    assert applied.success and applied.graph_updated
    assert graph.edges[applied.edge_id].status == VerificationStatus.SYMBOLIC_CHECKED


def test_registry_exposes_inner_product_family():
    from automate.theory.rules import RuleRegistry

    expected = {
        "vector_inner_product",
        "vector_norm",
        "vector_orthogonal",
        "vector_projection",
        "vector_gram_schmidt",
    }
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
