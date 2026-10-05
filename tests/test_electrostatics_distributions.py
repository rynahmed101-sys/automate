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
               "k*rho*dx/sqrt(x**2+y**2+z**2)", measure="dx")
    assert r.passed


def test_distribution_kernel_wrong_claim_rejected():
    assert not _check("continuous_charge_potential", "rho", "Vector([1,0,0])", "1").passed


def test_distribution_kernel_zero_separation_rejected():
    assert not _check("continuous_charge_field", "rho", "Vector([0,0,0])",
                       "Vector([0,0,0])").passed


def test_distribution_kernel_requires_explicit_measure():
    graph = DerivationGraph(id="continuous_charge_field")
    for nid, raw in [("rho", "rho"), ("d", "Vector([1,0,0])"), ("out", "Vector([k*rho,0,0])")]:
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=raw)))
    edge = DerivationEdge(
        id="e", input_nodes=["rho", "d"], output_nodes=["out"],
        transformation_rule="continuous_charge_field",
        justification="Explicit-measure contract",
        checker="electrostatics", parameters={"k": "k"},
    )
    assert not ElectrostaticsChecker().verify_edge(edge, graph).passed


def test_distribution_kernel_rejects_vector_measure():
    assert not _check(
        "continuous_charge_field", "rho", "Vector([1,0,0])",
        "Vector([k*rho,0,0])", measure="Vector([1,2])"
    ).passed


def test_distribution_kernel_rejects_unsafe_measure_expression():
    assert not _check(
        "continuous_charge_field", "rho", "Vector([1,0,0])",
        "Vector([k*rho,0,0])", measure="__import__('os').system('id')"
    ).passed


def test_distribution_rules_registered():
    from automate.theory.rules import RuleRegistry
    assert {"continuous_charge_field","continuous_charge_potential"}.issubset(
        set(RuleRegistry().list_rule_ids())
    )


def _line_check(density, observation, output, parameters):
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


def test_uniform_finite_x_line_charge_potential():
    result = _line_check("1", "Vector([0,1,0])", "2*k*asinh(1)",
        {"axis": "x", "source_bounds": ["-1", "1"], "coordinates": ["x", "y", "z"]})
    assert result.passed, result


def test_uniform_finite_y_line_charge_potential():
    result = _line_check("2", "Vector([1,0,0])", "4*k*asinh(1)",
        {"axis": "y", "source_bounds": ["-1", "1"], "coordinates": ["x", "y", "z"]})
    assert result.passed, result


def test_uniform_line_charge_wrong_claim_rejected():
    result = _line_check("1", "Vector([0,1,0])", "1",
        {"axis": "x", "source_bounds": ["-1", "1"], "coordinates": ["x", "y", "z"]})
    assert not result.passed


def test_uniform_line_charge_rejects_missing_geometry_contract():
    assert not _line_check("1", "Vector([0,1,0])", "2*k*asinh(1)",
        {"axis": "x", "source_bounds": ["-1", "1"]}).passed
    assert not _line_check("1", "Vector([0,0,0])", "0",
        {"axis": "x", "source_bounds": ["-1", "1"], "coordinates": ["x", "y", "z"]}).passed


def test_uniform_line_charge_rejects_unsafe_bounds():
    assert not _line_check("1", "Vector([0,1,0])", "2*k*asinh(1)",
        {"axis": "x", "source_bounds": ["-1", "__import__('os').system('id')"], "coordinates": ["x", "y", "z"]}).passed


def test_uniform_line_charge_rejects_nonpositive_interval():
    assert not _line_check("1", "Vector([0,1,0])", "2*k*asinh(1)",
        {"axis": "x", "source_bounds": ["1", "-1"], "coordinates": ["x", "y", "z"]}).passed


def test_uniform_line_charge_registry_exposes_rule():
    from automate.theory.rules import RuleRegistry
    assert "uniform_line_charge_potential" in RuleRegistry().list_rule_ids()
