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
    assert result.passed


def test_uniform_finite_y_line_charge_potential():
    result = _line_check("2", "Vector([1,0,0])", "4*k*asinh(1)",
        {"axis": "y", "source_bounds": ["-1", "1"], "coordinates": ["x", "y", "z"]})
    assert result.passed, result.details


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

def _gauss_check(field, rho, flux, parameters):
    graph = DerivationGraph(id="gauss_law")
    for nid, raw in [("field", field), ("rho", rho), ("flux", flux)]:
        graph.add_node(DerivationNode(id=nid, expression=MathematicalExpression(raw_str=raw)))
    edge = DerivationEdge(
        id="e", input_nodes=["field", "rho"], output_nodes=["flux"],
        transformation_rule="gauss_law_box",
        justification="Phase 2B bounded Gauss-law verification",
        checker="electrostatics", parameters=parameters,
    )
    return ElectrostaticsChecker().verify_edge(edge, graph)


def test_gauss_law_uniform_field_zero_charge_box():
    r = _gauss_check("Vector([1,0,0])", "0", "0",
        {"coordinates":["x","y","z"],"bounds":[["0","1"],["0","2"],["0","3"]],
         "epsilon0":"epsilon0","orientation":"outward"})
    assert r.passed


def test_gauss_law_radial_field_uniform_density_box():
    r = _gauss_check("Vector([rho*x/(3*epsilon0),rho*y/(3*epsilon0),rho*z/(3*epsilon0)])",
        "rho", "8*rho/epsilon0",
        {"coordinates":["x","y","z"],"bounds":[["-1","1"],["-1","1"],["-1","1"]],
         "epsilon0":"epsilon0","orientation":"outward"})
    assert r.passed


def test_gauss_law_rejects_wrong_flux():
    assert not _gauss_check("Vector([rho*x/(3*epsilon0),rho*y/(3*epsilon0),rho*z/(3*epsilon0)])",
        "rho", "0",
        {"coordinates":["x","y","z"],"bounds":[["-1","1"],["-1","1"],["-1","1"]],
         "epsilon0":"epsilon0","orientation":"outward"}).passed


def test_gauss_law_requires_outward_orientation():
    assert not _gauss_check("Vector([rho*x/(3*epsilon0),rho*y/(3*epsilon0),rho*z/(3*epsilon0)])",
        "rho", "8*rho/epsilon0",
        {"coordinates":["x","y","z"],"bounds":[["-1","1"],["-1","1"],["-1","1"]],
         "epsilon0":"epsilon0","orientation":"inward"}).passed


def test_gauss_law_rejects_invalid_box():
    assert not _gauss_check("Vector([rho*x/(3*epsilon0),rho*y/(3*epsilon0),rho*z/(3*epsilon0)])",
        "rho", "6*rho/epsilon0",
        {"coordinates":["x","y","z"],"bounds":[["1","0"],["-1","1"],["-1","1"]],
         "epsilon0":"epsilon0","orientation":"outward"}).passed


def test_gauss_law_rejects_unsafe_bound_expression():
    assert not _gauss_check("Vector([rho*x/(3*epsilon0),rho*y/(3*epsilon0),rho*z/(3*epsilon0)])",
        "rho", "6*rho/epsilon0",
        {"coordinates":["x","y","z"],"bounds":[["0","__import__('os').system('id')"],["-1","1"],["-1","1"]],
         "epsilon0":"epsilon0","orientation":"outward"}).passed


def test_gauss_law_registry_exposes_rule():
    from automate.theory.rules import RuleRegistry
    assert "gauss_law_box" in RuleRegistry().list_rule_ids()
