"""Named Phase 2A Vector Calculus acceptance campaign."""

from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, outputs, *, parameters=None):
    graph = DerivationGraph(id=f"vc_{rule}")
    in_ids = []
    for i, expr in enumerate(inputs):
        nid = f"in_{i}"
        in_ids.append(nid)
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=expr)))
    out_ids = []
    for i, expr in enumerate(outputs):
        nid = f"out_{i}"
        out_ids.append(nid)
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=expr)))
    edge = DerivationEdge(
        id="edge",
        input_nodes=in_ids,
        output_nodes=out_ids,
        transformation_rule=rule,
        justification="Phase 2A Vector Calculus acceptance",
        checker="vector_calculus",
        parameters=parameters or {},
    )
    return VectorCalculusChecker().verify_edge(edge, graph)


def test_field_declarations_are_identity_preserving():
    assert _check("scalar_field", ["x**2 + y"], ["x**2 + y"], parameters={"coordinates": ["x", "y"]}).passed
    assert _check("vector_field", ["Vector([x, y, z])"], ["Vector([x, y, z])"], parameters={"coordinates": ["x", "y", "z"]}).passed
    assert not _check("scalar_field", ["x"], ["x + 1"], parameters={"coordinates": ["x"]}).passed


def test_gradient_and_directional_derivative():
    report = _check(
        "gradient",
        ["x**2*y + z"],
        ["Vector([2*x*y, x**2, 1])"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.passed and report.status == VerificationStatus.SYMBOLIC_CHECKED

    report = _check(
        "gradient",
        ["x**2 + y**2"],
        ["Vector([2*x, 2*y])"],
        parameters={"coordinates": ["x", "y"]},
    )
    assert report.passed

    report = _check(
        "directional_derivative",
        ["x**2 + y", "Vector([1, 1])"],
        ["(2*x + 1)/sqrt(2)"],
        parameters={"coordinates": ["x", "y"]},
    )
    assert report.passed


def test_divergence_curl_and_laplacian():
    report = _check(
        "divergence",
        ["Vector([x**2, x*y, z**2])"],
        ["3*x + 2*z"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.passed

    report = _check(
        "curl",
        ["Vector([-y/2, x/2, z])"],
        ["Vector([0, 0, 1])"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.passed

    report = _check(
        "laplacian",
        ["x**2 + y**2 + z**2"],
        ["6"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.passed


def test_independent_finite_difference_evidence():
    report = _check(
        "gradient",
        ["x**2 + 3*y + z**2"],
        ["Vector([2*x, 3, 2*z])"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.passed
    evidence = report.details["finite_difference_cross_check"]
    assert evidence["independence_class"] == "DIFFERENT_ENGINE"
    assert evidence["passed"] is True

    report = _check(
        "divergence",
        ["Vector([x**2, y**2, z**2])"],
        ["2*x + 2*y + 2*z"],
        parameters={"coordinates": ["x", "y", "z"]},
    )
    assert report.details["finite_difference_cross_check"]["passed"] is True


def test_conservative_field_and_potential():
    report = _check(
        "conservative_field",
        ["Vector([2*x, 2*y])", "x**2 + y**2"],
        ["1"],
        parameters={"coordinates": ["x", "y"]},
    )
    assert report.passed

    report = _check(
        "conservative_field",
        ["Vector([-y, x])", "x*y"],
        ["0"],
        parameters={"coordinates": ["x", "y"]},
    )
    assert report.passed


def test_adversarial_wrong_results_are_rejected():
    assert not _check("gradient", ["x**2 + y**2"], ["Vector([x, 2*y])"], parameters={"coordinates": ["x", "y"]}).passed
    assert not _check("divergence", ["Vector([x, y])"], ["x"], parameters={"coordinates": ["x", "y"]}).passed
    assert not _check("curl", ["Vector([-y, x, z])"], ["Vector([0, 0, 0])"], parameters={"coordinates": ["x", "y", "z"]}).passed
    assert not _check("laplacian", ["x**2 + y**2"], ["2"], parameters={"coordinates": ["x", "y"]}).passed


def test_dimension_and_shape_contracts_fail_closed():
    assert not _check("gradient", ["x**2 + y**2"], ["Vector([2*x])"], parameters={"coordinates": ["x", "y"]}).passed
    assert not _check("curl", ["Vector([x, y])"], ["Vector([0, 0, 0])"], parameters={"coordinates": ["x", "y"]}).passed
    assert not _check("divergence", ["Vector([x, y, z])"], ["0"], parameters={"coordinates": ["x", "y"]}).passed
    assert not _check("directional_derivative", ["x**2", "Vector([0, 0])"], ["0"], parameters={"coordinates": ["x", "y"]}).passed


def test_coordinate_symbols_are_preserved():
    report = _check(
        "gradient",
        ["sin(x) + y**2"],
        ["Vector([cos(x), 2*y])"],
        parameters={"coordinates": ["x", "y"]},
    )
    assert report.passed
