"""Cartesian vector-calculus integration acceptance campaign."""

from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output, *, parameters):
    graph = DerivationGraph(id=f"integral_{rule}")
    in_ids = []
    for i, expr in enumerate(inputs):
        nid = f"in_{i}"
        in_ids.append(nid)
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=expr)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    edge = DerivationEdge(
        id="edge",
        input_nodes=in_ids,
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Phase 2A Cartesian integration acceptance",
        checker="vector_calculus",
        parameters=parameters,
    )
    return VectorCalculusChecker().verify_edge(edge, graph)


def test_scalar_and_vector_line_integrals():
    report = _check(
        "line_integral_scalar",
        ["1", "Vector([t, 0])"],
        "2",
        parameters={"variables": ["t"], "bounds": [[0, 2]], "coordinates": ["x", "y"]},
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["independent_numerical_check"]["independence_class"] == "DIFFERENT_ENGINE"
    assert report.details["independent_numerical_check"]["passed"] is True

    report = _check(
        "line_integral_vector",
        ["Vector([1, 0])", "Vector([t, 0])"],
        "2",
        parameters={"variables": ["t"], "bounds": [[0, 2]], "coordinates": ["x", "y"]},
    )
    assert report.passed, report.details
    assert report.details["independent_numerical_check"]["passed"] is True


def test_surface_integral_and_flux():
    report = _check(
        "surface_integral_scalar",
        ["1", "Vector([u, v, 0])"],
        "1",
        parameters={"variables": ["u", "v"], "bounds": [[0, 1], [0, 1]], "coordinates": ["x", "y", "z"]},
    )
    assert report.passed
    assert report.details["independent_numerical_check"]["passed"] is True

    report = _check(
        "surface_flux",
        ["Vector([0, 0, 1])", "Vector([u, v, 0])"],
        "1",
        parameters={"variables": ["u", "v"], "bounds": [[0, 1], [0, 1]], "coordinates": ["x", "y", "z"]},
    )
    assert report.passed
    assert report.details["independent_numerical_check"]["passed"] is True


def test_volume_integral():
    report = _check(
        "volume_integral",
        ["x + y + z"],
        "3/2",
        parameters={"variables": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]]},
    )
    assert report.passed
    assert report.details["independent_numerical_check"]["passed"] is True


def test_wrong_integrals_are_rejected():
    assert not _check(
        "line_integral_scalar", ["1", "Vector([t, 0])"], "1",
        parameters={"variables": ["t"], "bounds": [[0, 2]], "coordinates": ["x", "y"]},
    ).passed
    assert not _check(
        "line_integral_vector", ["Vector([x, 0])", "Vector([t, 0])"], "3",
        parameters={"variables": ["t"], "bounds": [[0, 2]], "coordinates": ["x", "y"]},
    ).passed
    assert not _check(
        "surface_flux", ["Vector([0, 0, 1])", "Vector([u, v, 0])"], "2",
        parameters={"variables": ["u", "v"], "bounds": [[0, 1], [0, 1]], "coordinates": ["x", "y", "z"]},
    ).passed
    assert not _check(
        "volume_integral", ["x + y + z"], "1",
        parameters={"variables": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]]},
    ).passed


def test_bounds_and_parameterization_contracts_fail_closed():
    assert not _check(
        "line_integral_scalar", ["1", "Vector([t, 0])"], "2",
        parameters={"variables": ["t"], "bounds": [[0, 2]]},
    ).passed
    assert not _check(
        "surface_integral_scalar", ["1", "Vector([u, v])"], "1",
        parameters={"variables": ["u", "v"], "bounds": [[0, 1], [0, 1]], "coordinates": ["x", "y", "z"]},
    ).passed
    assert not _check(
        "volume_integral", ["x + y"], "1",
        parameters={"variables": ["x", "y"], "bounds": [[0, 1], [0, 1]]},
    ).passed


def test_registry_exposes_integration_family():
    from automate.theory.rules import RuleRegistry
    expected = {
        "line_integral_scalar", "line_integral_vector",
        "surface_integral_scalar", "surface_flux", "volume_integral",
    }
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
