"""Bounded point-charge electrostatics acceptance campaign."""

from automate.backend.electrostatics_backend import ElectrostaticsChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression


def _check(rule, inputs, output, *, parameters=None):
    graph = DerivationGraph(id=f"electro_{rule}")
    ids = []
    for i, expr in enumerate(inputs):
        nid = f"in_{i}"
        ids.append(nid)
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=expr)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    edge = DerivationEdge(
        id="edge",
        input_nodes=ids,
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Phase 2B point-charge electrostatics acceptance",
        checker="electrostatics",
        parameters=parameters or {"k": "k"},
    )
    return ElectrostaticsChecker().verify_edge(edge, graph)


def test_coulomb_force():
    report = _check(
        "coulomb_force",
        ["2", "3", "Vector([0, 0])", "Vector([2, 0])"],
        "Vector([3*k/2, 0])",
    )
    assert report.passed


def test_point_charge_field():
    report = _check(
        "point_charge_field",
        ["2", "Vector([2, 0, 0])"],
        "Vector([k/2, 0, 0])",
    )
    assert report.passed


def test_point_charge_potential():
    report = _check(
        "point_charge_potential",
        ["2", "Vector([2, 0, 0])"],
        "k",
    )
    assert report.passed


def test_wrong_claims_fail_closed():
    assert not _check(
        "point_charge_field", ["q", "Vector([r, 0, 0])"], "Vector([k*q/r, 0, 0])"
    ).passed
    assert not _check(
        "point_charge_potential", ["q", "Vector([r, 0, 0])"], "k*q/r**2"
    ).passed


def test_coincident_positions_are_rejected():
    assert not _check(
        "coulomb_force",
        ["q1", "q2", "Vector([0, 0, 0])", "Vector([0, 0, 0])"],
        "Vector([0, 0, 0])",
    ).passed


def test_rule_registry_exposes_electrostatics():
    from automate.theory.rules import RuleRegistry
    expected = {"coulomb_force", "point_charge_field", "point_charge_potential"}
    assert expected.issubset(set(RuleRegistry().list_rule_ids()))
