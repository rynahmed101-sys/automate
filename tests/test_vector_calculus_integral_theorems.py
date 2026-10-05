"""Bounded integral-theorem acceptance campaign."""

from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, field, output, *, parameters):
    graph = DerivationGraph(id=f"theorem_{rule}")
    graph.add_node(DerivationNode(id="field", expression=MathematicalExpression(raw_str=field)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    edge = DerivationEdge(
        id="edge",
        input_nodes=["field"],
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Phase 2A integral theorem acceptance",
        checker="vector_calculus",
        parameters=parameters,
    )
    return VectorCalculusChecker().verify_edge(edge, graph)


def test_green_theorem_rectangle():
    report = _check(
        "green_theorem",
        "Vector([-y, x])",
        "0",
        parameters={"coordinates": ["x", "y"], "bounds": [[0, 1], [0, 1]], "orientation": "ccw"},
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED


def test_divergence_theorem_box():
    report = _check(
        "divergence_theorem",
        "Vector([x, y, z])",
        "0",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]], "orientation": "outward"},
    )
    assert report.passed


def test_stokes_theorem_planar_rectangle():
    report = _check(
        "stokes_theorem",
        "Vector([-y, x, 0])",
        "0",
        parameters={
            "coordinates": ["x", "y", "z"],
            "bounds": [[0, 1], [0, 1]],
            "z": 0,
            "orientation": "ccw_viewed_from_positive_normal",
        },
    )
    assert report.passed


def test_theorems_reject_wrong_orientation():
    assert not _check(
        "green_theorem", "Vector([-y, x])", "0",
        parameters={"coordinates": ["x", "y"], "bounds": [[0, 1], [0, 1]], "orientation": "clockwise"},
    ).passed
    assert not _check(
        "divergence_theorem", "Vector([x, y, z])", "0",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]], "orientation": "inward"},
    ).passed
    assert not _check(
        "stokes_theorem", "Vector([-y, x, 0])", "0",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1]], "z": 0, "orientation": "clockwise"},
    ).passed


def test_theorems_reject_wrong_claims():
    assert not _check(
        "green_theorem", "Vector([-y, x])", "1",
        parameters={"coordinates": ["x", "y"], "bounds": [[0, 1], [0, 1]], "orientation": "ccw"},
    ).passed
    assert not _check(
        "divergence_theorem", "Vector([x, y, z])", "1",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]], "orientation": "outward"},
    ).passed
    assert not _check(
        "stokes_theorem", "Vector([-y, x, 0])", "1",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1]], "z": 0, "orientation": "ccw_viewed_from_positive_normal"},
    ).passed


def test_theorems_require_explicit_contracts():
    assert not _check(
        "green_theorem", "Vector([-y, x])", "0",
        parameters={"coordinates": ["x", "y"], "bounds": [[0, 1], [0, 1]]},
    ).passed
    assert not _check(
        "divergence_theorem", "Vector([x, y, z])", "0",
        parameters={"coordinates": ["x", "y", "z"], "bounds": [[0, 1], [0, 1], [0, 1]]},
    ).passed


def test_registry_exposes_theorem_family():
    from automate.theory.rules import RuleRegistry
    expected = {"green_theorem", "divergence_theorem", "stokes_theorem"}
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
