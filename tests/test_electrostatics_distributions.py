"""Bounded continuous-charge electrostatics acceptance campaign."""

from automate.backend.electrostatics_backend import ElectrostaticsChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression


def _check(rule, rho, displacement, output, measure="1"):
    graph = DerivationGraph(id=rule)
    for nid, raw in [("rho", rho), ("d", displacement), ("out", output)]:
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=raw)))
    edge = DerivationEdge(
        id="e", input_nodes=["rho", "d"], output_nodes=["out"],
        transformation_rule=rule, justification="Phase 2B continuous charge kernel",
        checker="electrostatics", parameters={"k": "k", "density_measure": measure},
    )
    return ElectrostaticsChecker().verify_edge(edge, graph)


def test_continuous_charge_field_kernel():
    r = _check("continuous_charge_field", "rho", "Vector([x,y,z])",
               "Vector([k*rho*x/(x**2+y**2+z**2)**(3/2), k*rho*y/(x**2+y**2+z**2)**(3/2), k*rho*z/(x**2+y**2+z**2)**(3/2)])")
    assert r.passed


def test_continuous_charge_potential_kernel():
    r = _check("continuous_charge_potential", "rho", "Vector([x,y,z])",
               "k*rho/sqrt(x**2+y**2+z**2)", measure="dx")
    assert r.passed


def test_distribution_kernel_wrong_claim_rejected():
    assert not _check("continuous_charge_potential", "rho", "Vector([1,0,0])", "1").passed


def test_distribution_kernel_zero_separation_rejected():
    assert not _check("continuous_charge_field", "rho", "Vector([0,0,0])",
                       "Vector([0,0,0])").passed


def test_distribution_rules_registered():
    from automate.theory.rules import RuleRegistry
    assert {"continuous_charge_field","continuous_charge_potential"}.issubset(
        set(RuleRegistry().list_rule_ids())
    )
