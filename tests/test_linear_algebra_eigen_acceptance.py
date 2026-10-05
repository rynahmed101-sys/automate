"""Named Phase 1A eigenproblem capability acceptance campaign."""

from automate.ai.proposals import apply_and_verify_proposal
from automate.ai.schemas import DerivationProposal
from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _graph(rule, inputs, outputs, *, parameters=None):
    graph = DerivationGraph(id=f"linear_algebra_eigen_{rule}")
    input_ids = []
    for index, expression in enumerate(inputs):
        node_id = f"in_{index}"
        input_ids.append(node_id)
        graph.add_node(DerivationNode(
            id=node_id,
            expression=MathematicalExpression(raw_str=expression),
        ))
    output_ids = []
    for index, expression in enumerate(outputs):
        node_id = f"out_{index}"
        output_ids.append(node_id)
        graph.add_node(DerivationNode(
            id=node_id,
            expression=MathematicalExpression(raw_str=expression),
        ))
    graph.add_edge(DerivationEdge(
        id="edge",
        input_nodes=input_ids,
        output_nodes=output_ids,
        transformation_rule=rule,
        justification="Phase 1A eigenproblem acceptance",
        checker="linear_algebra",
        parameters=parameters or {},
    ))
    return graph, graph.edges["edge"]


def _check(rule, inputs, output=None, *, parameters=None, outputs=None):
    graph, edge = _graph(
        rule,
        inputs,
        outputs if outputs is not None else [output],
        parameters=parameters,
    )
    return LinearAlgebraChecker().verify_edge(edge, graph)


def test_characteristic_polynomial_exact_and_numeric_cross_check():
    report = _check(
        "matrix_characteristic_polynomial",
        ["Matrix([[2, 1], [1, 2]])"],
        "lam**2 - 4*lam + 3",
        parameters={"symbol": "lam"},
    )
    assert report.passed, report.error_message
    assert report.details["expected"] == "lam**2 - 4*lam + 3"
    assert report.details["numpy_cross_check"]["engine"] == "numpy.poly"
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_eigenvalues_preserve_multiplicity_and_ignore_order():
    report = _check("matrix_eigenvalues", ["Matrix([[2, 1], [1, 2]])"], "Vector([3, 1])")
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"

    repeated = _check("matrix_eigenvalues", ["Matrix([[2, 1], [0, 2]])"], "Vector([2, 2])")
    assert repeated.passed, repeated.error_message


def test_symbolic_eigenvalues():
    report = _check("matrix_eigenvalues", ["Matrix([[a, 0], [0, b]])"], "Vector([a, b])")
    assert report.passed, report.error_message
    assert report.details["numpy_cross_check"]["available"] is False


def test_eigenvector_residual_semantics_allow_any_valid_scaling():
    report = _check(
        "matrix_eigenvector",
        ["Matrix([[2, 1], [1, 2]])"],
        "Vector([2, 2])",
        parameters={"eigenvalue": "3"},
    )
    assert report.passed, report.error_message
    assert report.details["residual"] == ["0", "0"]
    assert report.details["numpy_cross_check"]["passed"] is True


def test_symbolic_eigenvector():
    report = _check(
        "matrix_eigenvector",
        ["Matrix([[a, 0], [0, b]])"],
        "Vector([1, 0])",
        parameters={"eigenvalue": "a"},
    )
    assert report.passed, report.error_message


def test_diagonalization_exact_and_numeric_cross_check():
    report = _check(
        "matrix_diagonalize",
        ["Matrix([[2, 1], [1, 2]])"],
        outputs=[
            "Matrix([[1, 1], [1, -1]])",
            "Matrix([[3, 0], [0, 1]])",
        ],
    )
    assert report.passed, report.error_message
    assert report.details["symbolic_equivalence"] is True
    assert report.details["numpy_cross_check"]["passed"] is True


def test_adversarial_eigenproblem_rejections():
    report = _check(
        "matrix_characteristic_polynomial",
        ["Matrix([[2, 1], [1, 2]])"],
        "lam**2 - 3*lam + 3",
        parameters={"symbol": "lam"},
    )
    assert not report.passed and report.status == VerificationStatus.FAILED

    report = _check("matrix_eigenvalues", ["Matrix([[2, 1], [1, 2]])"], "Vector([3, 2])")
    assert not report.passed

    report = _check("matrix_eigenvalues", ["Matrix([[2, 1], [0, 2]])"], "Vector([2])")
    assert not report.passed

    report = _check(
        "matrix_eigenvector",
        ["Matrix([[2, 1], [1, 2]])"],
        "Vector([0, 0])",
        parameters={"eigenvalue": "3"},
    )
    assert not report.passed and "non-zero" in (report.error_message or "").lower()

    report = _check(
        "matrix_eigenvector",
        ["Matrix([[2, 1], [1, 2]])"],
        "Vector([1, 0])",
        parameters={"eigenvalue": "3"},
    )
    assert not report.passed

    report = _check(
        "matrix_diagonalize",
        ["Matrix([[1, 1], [0, 1]])"],
        outputs=[
            "Matrix([[1, 1], [0, 1]])",
            "Matrix([[1, 0], [0, 1]])",
        ],
    )
    assert not report.passed

    report = _check(
        "matrix_diagonalize",
        ["Matrix([[2, 1], [1, 2]])"],
        outputs=[
            "Matrix([[1, 1], [1, -1]])",
            "Matrix([[3, 1], [0, 1]])",
        ],
    )
    assert not report.passed


def test_shape_and_domain_rejections():
    report = _check(
        "matrix_eigenvalues",
        ["Matrix([[1, 2, 3], [4, 5, 6]])"],
        "Vector([1, 2])",
    )
    assert not report.passed

    report = _check(
        "matrix_eigenvector",
        ["Matrix([[1, 0], [0, 2]])"],
        "Vector([1, 2, 3])",
        parameters={"eigenvalue": "1"},
    )
    assert not report.passed


def test_symbol_parameter_boundary():
    report = _check(
        "matrix_characteristic_polynomial",
        ["Matrix([[lam, 0], [0, 2]])"],
        "lam**2 - (lam + 2)*lam + 2*lam",
        parameters={"symbol": "lam"},
    )
    assert not report.passed and "must not appear" in (report.error_message or "")


def test_ai_diagonalization_proposal_path():
    graph = DerivationGraph(id="ai_linear_algebra_diagonalize")
    graph.add_node(DerivationNode(
        id="A",
        expression=MathematicalExpression(
            raw_str="Matrix([[2, 1], [1, 2]])",
            ast={"kind": "matrix", "shape": [2, 2]},
        ),
        node_kind="matrix",
    ))
    proposal = DerivationProposal(
        proposal_id="la_diag_agent_001",
        input_nodes=["A"],
        output_nodes=[
            {"id": "P", "expression": "Matrix([[1, 1], [1, -1]])", "node_kind": "matrix"},
            {"id": "D", "expression": "Matrix([[3, 0], [0, 1]])", "node_kind": "matrix"},
        ],
        rule="matrix_diagonalize",
        justification="P diagonalizes A into D.",
        target_checker="linear_algebra",
        origin={"type": "ai", "provider": "acceptance"},
    )
    dry = apply_and_verify_proposal(proposal, graph, dry_run=True)
    assert dry.success and not dry.graph_updated and "P" not in graph.nodes
    applied = apply_and_verify_proposal(proposal, graph, dry_run=False)
    assert applied.success and applied.graph_updated
    assert graph.edges[applied.edge_id].status == VerificationStatus.SYMBOLIC_CHECKED


def test_ai_malformed_linear_algebra_proposal_fails_closed():
    from automate.ai.validation import validate_ai_proposal
    raw = {
        "schema_version": "automate.proposal.v1",
        "proposal_id": "la_bad_eigen",
        "input_nodes": [],
        "output_nodes": [{"id": "out", "expression": "Matrix([[1, 2], [3]])"}],
        "rule": "matrix_eigenvalues",
        "justification": "malformed matrix",
        "target_checker": "linear_algebra",
    }
    result = validate_ai_proposal(raw)
    assert not result.is_valid
    assert any("inconsistent lengths" in error.lower() for error in result.errors)


def test_registry_exposes_eigenproblem_family():
    from automate.theory.rules import RuleRegistry
    expected = {
        "matrix_characteristic_polynomial",
        "matrix_eigenvalues",
        "matrix_eigenvector",
        "matrix_diagonalize",
    }
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
