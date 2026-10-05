"""Workload-oriented Maths/Physics acceptance campaign.

These tests exercise the current supported rule families with representative real
mathematics and physics, plus explicit negative cases. Passing this file does not
mean Automate solves arbitrary mathematics. It means the declared supported
interfaces behave correctly for these representative workloads.
"""

import json

import numpy as np
import pytest
import sympy as sp
from click.testing import CliRunner

from automate.cli import main
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.mechanics.lagrangian import LagrangianSystem
from automate.tensors.algebra import TensorGeometry
from automate.tensors.einsteinpy_adapter import cross_check_geometry, is_einsteinpy_available


def _graph_edge(rule, input_exprs, output_expr, *, parameters=None, checker="sympy"):
    graph = DerivationGraph(id=f"campaign_{rule}")
    input_ids = []
    for i, expr in enumerate(input_exprs):
        node_id = f"in_{i}"
        input_ids.append(node_id)
        graph.add_node(
            DerivationNode(
                id=node_id,
                expression=MathematicalExpression(raw_str=expr),
            )
        )
    graph.add_node(
        DerivationNode(
            id="out",
            expression=MathematicalExpression(raw_str=output_expr),
        )
    )
    edge = DerivationEdge(
        id="edge",
        input_nodes=input_ids,
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Automate real-workload acceptance campaign",
        checker=checker,
        parameters=parameters or {},
    )
    graph.add_edge(edge)
    return graph, edge


@pytest.mark.parametrize(
    "in_expr,out_expr",
    [
        ("x**2 + 2*x + 1", "(x + 1)**2"),
        ("sin(x)**2 + cos(x)**2", "1"),
        ("(a+b)**2", "a**2 + 2*a*b + b**2"),
        ("(x-y)*(x+y)", "x**2-y**2"),
        ("exp(x)*exp(y)", "exp(x+y)"),
        ("(2*x + 3)*(x - 1)", "2*x**2 + x - 3"),
        ("x**4 - 1", "(x**2 - 1)*(x**2 + 1)"),
        ("(a-b)*(a+b)", "a**2-b**2"),
    ],
)
def test_campaign_algebraic_identity_cases(in_expr, out_expr):
    graph, edge = _graph_edge("algebraic_identity", [in_expr], out_expr)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, f"{in_expr} != {out_expr}: {report.error_message}"
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED


@pytest.mark.parametrize(
    "in_expr,out_expr,wrt",
    [
        ("x**2", "2*x", "x"),
        ("sin(x)", "cos(x)", "x"),
        ("exp(x)", "exp(x)", "x"),
        ("x**3 + 4*x", "3*x**2 + 4", "x"),
        ("sin(2*x)", "2*cos(2*x)", "x"),
        ("x**2 + y**2", "2*x", "x"),
    ],
)
def test_campaign_calculus_derivatives(in_expr, out_expr, wrt):
    graph, edge = _graph_edge(
        "differentiate_both_sides",
        [in_expr],
        out_expr,
        parameters={"wrt": wrt},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED


@pytest.mark.parametrize(
    "in_expr,out_expr,from_expr,to_expr",
    [
        ("x + 2", "y + 3", "x", "y + 1"),
        ("x**2 + 2*x", "y**2 + 2*y", "x", "y"),
        ("sin(x) + x", "sin(z) + z", "x", "z"),
        ("a*x + b", "a*(y+1) + b", "x", "y+1"),
    ],
)
def test_campaign_substitution(in_expr, out_expr, from_expr, to_expr):
    graph, edge = _graph_edge(
        "substitute",
        [in_expr],
        out_expr,
        parameters={"from": from_expr, "to": to_expr},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message


@pytest.mark.parametrize(
    "in_expr,out_expr",
    [
        ("(x + 1)**2 - (x**2 + 2*x + 1)", "0"),
        ("(a-b)**2", "a**2 - 2*a*b + b**2"),
        ("(x + y)**3", "x**3 + 3*x**2*y + 3*x*y**2 + y**3"),
        ("(x**2 + 2*x + 1) - (x + 1)**2", "0"),
    ],
)
def test_campaign_simplification(in_expr, out_expr):
    graph, edge = _graph_edge("simplify", [in_expr], out_expr)
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message


@pytest.mark.parametrize(
    "ode,solution,parameters",
    [
        ("x_ddot + x", "C1*cos(t) + C2*sin(t)", {}),
        ("x_ddot - x", "C1*exp(t) + C2*exp(-t)", {}),
        ("x_ddot + 4*x", "A*cos(2*t + phi)", {}),
        ("x_ddot + 9*x", "A*cos(3*t + phi)", {}),
        ("x_ddot", "C1*t + C2", {}),
        ("diff(x(t), t, 2) + 4*x(t)", "A*cos(2*t + phi)", {}),
    ],
)
def test_campaign_ode_solution_verification(ode, solution, parameters):
    graph, edge = _graph_edge(
        "verify_ode_solution",
        [ode],
        solution,
        parameters={"coordinates": ["x"], "parameters": parameters},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, f"ODE {ode} / {solution}: {report.error_message}"


def test_campaign_wrong_ode_solution_rejected():
    graph, edge = _graph_edge(
        "verify_ode_solution",
        ["x_ddot + 4*x"],
        "A*cos(3*t + phi)",
        parameters={"coordinates": ["x"], "parameters": {}},
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED


@pytest.mark.parametrize(
    "lagrangian,coords,parameters",
    [
        ("m*x_dot**2/2-k*x**2/2", ["x"], {"m": "positive", "k": "positive"}),
        ("m*x_dot**2/2-m*g*x", ["x"], {"m": "positive", "g": "positive"}),
        (
            "m*(r_dot**2+r**2*theta_dot**2)/2-k*r**2/2",
            ["r", "theta"],
            {"m": "positive", "k": "positive"},
        ),
        (
            "m*l**2*theta_dot**2/2 + m*g*l*cos(theta)",
            ["theta"],
            {"m": "positive", "g": "positive", "l": "positive"},
        ),
    ],
)
def test_campaign_mechanics_cross_checks(lagrangian, coords, parameters):
    system = LagrangianSystem(lagrangian, coords, parameters=parameters)
    report = system.cross_check_euler_lagrange()
    assert report["all_matched"], report["discrepancies"]


@pytest.mark.parametrize(
    "lagrangian,coords,parameters,candidate",
    [
        (
            "m*x_dot**2/2-k*x**2/2",
            ["x"],
            {"m": "positive", "k": "positive"},
            "m*x_ddot + k*x",
        ),
        (
            "m*x_dot**2/2-m*g*x",
            ["x"],
            {"m": "positive", "g": "positive"},
            "m*x_ddot + m*g",
        ),
        (
            "m*l**2*theta_dot**2/2 + m*g*l*cos(theta)",
            ["theta"],
            {"m": "positive", "g": "positive", "l": "positive"},
            "m*l**2*theta_ddot + m*g*l*sin(theta)",
        ),
    ],
)
def test_campaign_mechanics_eom_verification(lagrangian, coords, parameters, candidate):
    system = LagrangianSystem(lagrangian, coords, parameters=parameters)
    passed, _, _, err = system.verify_euler_lagrange(candidate)
    assert passed, err


@pytest.mark.parametrize(
    "lagrangian,fields,coordinates,parameters,candidate",
    [
        ("d_x_phi**2/2", ["phi"], ["x"], {}, "diff(phi, x, 2)"),
        (
            "d_x_phi**2/2-m**2*phi**2/2",
            ["phi"],
            ["x"],
            {"m": "positive"},
            "diff(phi, x, 2)+m**2*phi",
        ),
    ],
)
def test_campaign_field_equations(lagrangian, fields, coordinates, parameters, candidate):
    graph, edge = _graph_edge(
        "vary_action",
        [lagrangian],
        candidate,
        parameters={
            "fields": fields,
            "coordinates": coordinates,
            "parameters": parameters,
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message


def test_campaign_field_wrong_equation_rejected():
    graph, edge = _graph_edge(
        "vary_action",
        ["d_x_phi**2/2-m**2*phi**2/2"],
        "diff(phi, x, 2)-m**2*phi",
        parameters={
            "fields": ["phi"],
            "coordinates": ["x"],
            "parameters": {"m": "positive"},
        },
    )
    report = SymPyChecker().verify_edge(edge, graph)
    assert report.passed is False
    assert report.status == VerificationStatus.FAILED


def _polar_metric():
    r, theta = sp.symbols("r theta", positive=True)
    return sp.Matrix([[1, 0], [0, r**2]]), [r, theta]


def _sphere_metric():
    theta, phi = sp.symbols("theta phi", real=True)
    r = sp.Symbol("r", positive=True)
    return sp.Matrix([[r**2, 0], [0, r**2 * sp.sin(theta)**2]]), [theta, phi], r


def _flat_metric():
    x, y = sp.symbols("x y", real=True)
    return sp.eye(2), [x, y]


def test_campaign_flat_geometry():
    metric, coords = _flat_metric()
    geom = TensorGeometry(metric, coords, simplify=True)
    assert all(v == 0 for v in geom.christoffel_symbols().values())
    assert all(v == 0 for v in geom.riemann_tensor().values())
    assert geom.ricci_tensor() == sp.zeros(2, 2)
    assert geom.ricci_scalar() == 0
    assert geom.einstein_tensor() == sp.zeros(2, 2)
    passed, _ = geom.verify_contracted_bianchi_identity()
    assert passed


def test_campaign_polar_geometry():
    metric, coords = _polar_metric()
    geom = TensorGeometry(metric, coords, simplify=True)
    gamma = geom.christoffel_symbols()
    r = coords[0]
    assert sp.simplify(gamma[(0, 1, 1)] + r) == 0
    assert sp.simplify(gamma[(1, 0, 1)] - 1/r) == 0
    assert sp.simplify(gamma[(1, 1, 0)] - 1/r) == 0
    passed, _ = geom.verify_contracted_bianchi_identity()
    assert passed


def test_campaign_sphere_geometry():
    metric, coords, r = _sphere_metric()
    geom = TensorGeometry(metric, coords, simplify=True)
    assert sp.simplify(geom.ricci_scalar() - 2/r**2) == 0
    G = geom.einstein_tensor()
    ricci = geom.ricci_tensor()
    scalar = geom.ricci_scalar()
    assert all(
        sp.simplify(G[i, j] - (ricci[i, j] - sp.Rational(1, 2)*geom.g[i, j]*scalar)) == 0
        for i in range(2) for j in range(2)
    )
    passed, _ = geom.verify_contracted_bianchi_identity()
    assert passed


def test_campaign_sphere_riemann_nonzero():
    metric, coords, _ = _sphere_metric()
    geom = TensorGeometry(metric, coords, simplify=True)
    assert any(v != 0 for v in geom.riemann_tensor().values())


def test_campaign_geometry_einsteinpy_cross_check():
    if not is_einsteinpy_available():
        pytest.skip("EinsteinPy is not available in this runtime")
    metric, coords = _polar_metric()
    native = TensorGeometry(metric, coords, simplify=True)
    report = cross_check_geometry(
        metric,
        coords,
        native_christoffel=native.christoffel_symbols(),
        native_ricci=native.ricci_tensor(),
        native_ricci_scalar=native.ricci_scalar(),
        native_einstein=native.einstein_tensor(),
    )
    assert report["execution_status"] == "COMPLETED", report.get("error")
    assert report["all_matched"] is True, report.get("discrepancies")


def test_campaign_harmonic_oscillator_dimensions():
    from automate.theory.parser import parse_theory_file
    graph = parse_theory_file("examples/harmonic_oscillator.yaml")
    edge = graph.get_edge("edge_euler_lagrange")
    report = DimensionChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.DIMENSIONALLY_CHECKED


def test_campaign_numerical_harmonic_oscillator():
    graph = DerivationGraph(id="campaign_numerical")
    graph.add_node(DerivationNode(
        id="eom",
        expression=MathematicalExpression(raw_str="m*x_ddot+k*x"),
    ))
    graph.add_node(DerivationNode(
        id="traj",
        expression=MathematicalExpression(raw_str="numerical_trajectory"),
    ))
    edge = DerivationEdge(
        id="edge",
        input_nodes=["eom"],
        output_nodes=["traj"],
        transformation_rule="numerical_simulation",
        justification="RK45 acceptance campaign",
        checker="numerical",
        parameters={
            "coordinates": ["x"],
            "parameters": {"m": "positive", "k": "positive"},
            "numerical_parameters": {"m": 1.0, "k": 4.0},
            "initial_conditions": {"x": 1.0},
            "initial_velocities": {"x": 0.0},
            "t_max": 10.0,
        },
    )
    graph.add_edge(edge)
    report = NumericalChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.NUMERICALLY_CHECKED
    assert report.details["metrics"]["solver_method"] == "RK45"


def test_campaign_statistical_fit():
    t = np.linspace(0, 10, 50)
    rng = np.random.default_rng(20261005)
    x = np.cos(2.0*t) + 0.03*rng.normal(size=t.size)
    graph = DerivationGraph(id="campaign_statistics")
    graph.add_node(DerivationNode(
        id="sol",
        expression=MathematicalExpression(raw_str="A*cos(omega*t+phi)"),
    ))
    graph.add_node(DerivationNode(
        id="fit",
        expression=MathematicalExpression(raw_str="omega_fit"),
    ))
    edge = DerivationEdge(
        id="edge",
        input_nodes=["sol"],
        output_nodes=["fit"],
        transformation_rule="empirical_inference",
        justification="Synthetic observation recovery acceptance campaign",
        checker="statistical",
        parameters={
            "model": "cosine",
            "A": 1.0,
            "omega": 2.0,
            "phi": 0.0,
            "t_data": t.tolist(),
            "x_obs": x.tolist(),
            "noise_std": 0.03,
            "data_source": "observed",
            "data_id": "campaign-sho-omega-20261005",
        },
    )
    graph.add_edge(edge)
    report = StatisticalChecker().verify_edge(edge, graph)
    assert report.passed, report.error_message
    assert report.status == VerificationStatus.STATISTICALLY_CHECKED
    assert report.details["data_provenance"]["sha256"]
    assert abs(report.details["parameter_estimates"]["omega"]["estimate"] - 2.0) < 0.1


def test_campaign_machine_contract_and_capabilities():
    from pathlib import Path

    runner = CliRunner()
    capabilities = runner.invoke(main, ["capabilities", "--json"])
    assert capabilities.exit_code == 0, capabilities.output
    caps = json.loads(capabilities.output)
    assert caps["agent_contract"]["schema_version"] == "automate.agent.v1"
    assert caps["rule_registry"]["count"] == 66

    contract_result = runner.invoke(main, ["schema", "--name", "agent"])
    assert contract_result.exit_code == 0, contract_result.output
    contract = json.loads(contract_result.output)
    assert contract["schema_version"] == "automate.agent.v1"
    assert len(contract["rules"]) == 66
    assert set([
        "discover","parse","context","validate","propose_dry_run","propose_apply",
        "research","check","prove","simulate","stats","query_assumptions",
        "expand","visualize","report","export_certificate","schema","demo"
    ]).issubset(contract["commands"])
    assert Path("schemas/automate-agent-v1.json").exists()
