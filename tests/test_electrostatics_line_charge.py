"""Finite uniform line-charge potential acceptance campaign."""

from automate.backend.electrostatics_backend import ElectrostaticsChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression


def _check(density, observation, output, parameters):
    graph = DerivationGraph(id="line_charge")
    for nid, expr in [("density", density), ("obs", observation), ("out", output)]:
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=expr)))
    edge = DerivationEdge(
        id="e", input_nodes=["density", "obs"], output_nodes=["out"],
        transformation_rule="uniform_line_charge_potential",
        justification="Phase 2B finite line-charge acceptance",
        checker="electrostatics", parameters=parameters,
    )
    return ElectrostaticsChecker().verify_edge(edge, graph)


def test_uniform_x_axis_line_charge_potential():
    r = _check("1", "Vector([0, 1, 0])", "2*k*asinh(1)",
               {"axis":"x","source_bounds":[-1,1],"coordinates":["x","y","z"]})
    assert r.passed


def test_uniform_y_axis_line_charge_potential():
    r = _check("2", "Vector([1, 0, 0])", "4*k*asinh(1)",
               {"axis":"y","source_bounds":[-1,1],"coordinates":["x","y","z"]})
    assert r.passed


def test_wrong_claim_is_rejected():
    r = _check("1", "Vector([0, 1, 0])", "1",
               {"axis":"x","source_bounds":[-1,1],"coordinates":["x","y","z"]})
    assert not r.passed


def test_missing_geometry_contract_fails_closed():
    assert not _check("1", "Vector([0,1,0])", "2*k*asinh(1)",
                       {"axis":"x","source_bounds":[-1,1]}).passed
    assert not _check("1", "Vector([0,0,0])", "0",
                       {"axis":"x","source_bounds":[-1,1],"coordinates":["x","y","z"]}).passed


def test_rule_registry_exposes_line_charge():
    from automate.theory.rules import RuleRegistry
    assert "uniform_line_charge_potential" in RuleRegistry().list_rule_ids()
