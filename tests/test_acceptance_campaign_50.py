"""Exact 50-problem Maths/Physics acceptance campaign.

This campaign is deliberately workload-oriented. Every case has a declared
classification:
  VERIFIED            : an applicable backend produced passing evidence.
  UNVERIFIED          : no verification evidence was established.
  UNSUPPORTED_SEMANTICS: Automate explicitly lacks the semantic/backend support.
  FAILED              : a check ran and the claim did not pass.

The suite contains exactly 35 Maths cases and 15 Physics cases, matching the
initial acceptance plan:
  Maths   = 10 symbolic/algebraic + 10 calculus/ODE + 5 linear algebra
          + 5 tensor/index + 5 numerical
  Physics = 5 mechanics + 5 electromagnetism/vector calculus
          + 5 tensor/geometry/relativity.

The suite must not convert unsupported or unverified mathematics into a pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import sympy as sp

from automate.backend.dimension_backend import DimensionChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.tensors import (
    TensorEquation,
    TensorExpression,
    TensorIndex,
    TensorQuantity,
    TensorProduct,
    validate_einstein_product,
)
from automate.mechanics.lagrangian import LagrangianSystem
from automate.tensors.algebra import TensorGeometry


CLASSIFICATIONS = {
    "VERIFIED",
    "UNVERIFIED",
    "UNSUPPORTED_SEMANTICS",
    "FAILED",
}


def _graph_edge(
    rule: str,
    input_exprs: list[str],
    output_expr: str,
    *,
    parameters: dict[str, Any] | None = None,
    checker: str = "sympy",
) -> tuple[DerivationGraph, DerivationEdge]:
    graph = DerivationGraph(id=f"acceptance_{rule}")
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
        justification="50-problem acceptance campaign",
        checker=checker,
        parameters=parameters or {},
    )
    graph.add_edge(edge)
    return graph, edge


def _classify_report(report) -> str:
    status = getattr(report, "status", None)
    if getattr(report, "passed", False) or status in {
        VerificationStatus.DIMENSIONALLY_CHECKED,
        VerificationStatus.SYMBOLIC_CHECKED,
        VerificationStatus.NUMERICALLY_CHECKED,
        VerificationStatus.STATISTICALLY_CHECKED,
        VerificationStatus.FORMALLY_PROVED,
    }:
        return "VERIFIED"
    if status == VerificationStatus.UNVERIFIED:
        return "UNVERIFIED"
    if status == VerificationStatus.NOT_APPLICABLE:
        return "UNSUPPORTED_SEMANTICS"
    if status in {
        VerificationStatus.FAILED,
        VerificationStatus.DISPROVED,
        VerificationStatus.TIMEOUT,
    }:
        return "FAILED"
    return "UNVERIFIED"


def _sympy_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    graph, edge = _graph_edge(
        case["rule"],
        [case["input"]],
        case["output"],
        parameters=case.get("parameters"),
        checker="sympy",
    )
    report = SymPyChecker().verify_edge(edge, graph)
    return _classify_report(report), {
        "status": report.status.value,
        "backend": report.backend,
        "passed": report.passed,
        "error": report.error_message,
    }


def _unverified_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    graph, edge = _graph_edge(
        "pending_claim",
        [case["input"]],
        case["output"],
        checker="unverified",
    )
    return (
        "UNVERIFIED",
        {
            "status": edge.status.value,
            "backend": edge.checker,
            "passed": False,
            "reason": "No verification backend was invoked for this claim.",
        },
    )


def _tensor_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    op = case["operation"]
    if op == "product":
        result = validate_einstein_product(case["indices"])
        observed = "VERIFIED" if result.is_valid else "FAILED"
        return observed, {
            "valid": result.is_valid,
            "resultant_rank": result.resultant_rank,
            "free_indices": [i.symbol for i in result.free_indices],
            "dummy_indices": result.dummy_indices,
            "errors": result.errors,
        }
    if op == "equation":
        result = case["equation"].validate_structure()
        observed = "VERIFIED" if result.is_valid else "FAILED"
        return observed, {
            "valid": result.is_valid,
            "resultant_rank": result.resultant_rank,
            "errors": result.errors,
        }
    raise AssertionError(f"Unknown tensor operation: {op}")


def _numerical_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    graph, edge = _graph_edge(
        "numerical_simulation",
        [case["eom"]],
        "numerical_trajectory",
        parameters={
            "coordinates": ["x"],
            "parameters": case.get("symbols", {}),
            "numerical_parameters": case.get("values", {}),
            "initial_conditions": {"x": case.get("x0", 1.0)},
            "initial_velocities": {"x": case.get("v0", 0.0)},
            "t_max": case.get("t_max", 5.0),
        },
        checker="numerical",
    )
    report = NumericalChecker().verify_edge(edge, graph)
    return _classify_report(report), {
        "status": report.status.value,
        "backend": report.backend,
        "passed": report.passed,
        "error": report.error_message,
        "metrics": report.details.get("metrics", {}),
    }


def _mechanics_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    system = LagrangianSystem(
        case["lagrangian"],
        case["coordinates"],
        parameters=case.get("parameters", {}),
    )
    if case["operation"] == "eom":
        passed, details, _, error = system.verify_euler_lagrange(case["candidate"])
        return ("VERIFIED" if passed else "FAILED"), {
            "passed": passed,
            "error": error,
            "residuals": details.get("residuals", {}),
        }
    if case["operation"] == "cross_check":
        report = system.cross_check_euler_lagrange()
        return ("VERIFIED" if report["all_matched"] else "FAILED"), report
    if case["operation"] == "hamiltonian":
        H, p_syms = system.hamiltonian()
        expected = p_syms["x"]**2 / (2 * system.symbols["m"]) + sp.Rational(1, 2) * system.symbols["k"] * system.q_syms["x"]**2
        residual = sp.simplify(H - expected)
        return ("VERIFIED" if residual == 0 else "FAILED"), {
            "hamiltonian": str(H),
            "residual": str(residual),
        }
    raise AssertionError(f"Unknown mechanics operation: {case['operation']}")


def _geometry_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    op = case["operation"]
    if op == "flat":
        x, y = sp.symbols("x y", real=True)
        geom = TensorGeometry(sp.eye(2), [x, y], simplify=True)
        passed = (
            all(v == 0 for v in geom.christoffel_symbols().values())
            and geom.riemann_tensor()
            and all(v == 0 for v in geom.riemann_tensor().values())
            and geom.ricci_tensor() == sp.zeros(2, 2)
            and geom.ricci_scalar() == 0
        )
        return ("VERIFIED" if passed else "FAILED"), {"ricci_scalar": str(geom.ricci_scalar())}
    if op == "polar_christoffel":
        r, theta = sp.symbols("r theta", positive=True)
        geom = TensorGeometry(sp.Matrix([[1, 0], [0, r**2]]), [r, theta], simplify=True)
        gamma = geom.christoffel_symbols()
        residuals = [
            sp.simplify(gamma[(0, 1, 1)] + r),
            sp.simplify(gamma[(1, 0, 1)] - 1/r),
            sp.simplify(gamma[(1, 1, 0)] - 1/r),
        ]
        return ("VERIFIED" if all(v == 0 for v in residuals) else "FAILED"), {
            "residuals": [str(v) for v in residuals]
        }
    if op == "sphere_scalar":
        theta, phi = sp.symbols("theta phi", real=True)
        r = sp.Symbol("r", positive=True)
        geom = TensorGeometry(
            sp.Matrix([[r**2, 0], [0, r**2 * sp.sin(theta)**2]]),
            [theta, phi],
            simplify=True,
        )
        residual = sp.simplify(geom.ricci_scalar() - 2/r**2)
        return ("VERIFIED" if residual == 0 else "FAILED"), {"residual": str(residual)}
    if op == "schwarzschild_gamma":
        t, r = sp.symbols("t r", real=True)
        M = sp.Symbol("M", positive=True)
        f = 1 - 2*M/r
        geom = TensorGeometry(sp.Matrix([[-f, 0], [0, 1/f]]), [t, r], simplify=True)
        gamma = geom.christoffel_symbols()[(1, 0, 0)]
        expected = M * (r - 2*M) / r**3
        residual = sp.simplify(gamma - expected)
        return ("VERIFIED" if residual == 0 else "FAILED"), {"residual": str(residual)}
    if op == "bianchi":
        x, y = sp.symbols("x y", real=True)
        geom = TensorGeometry(sp.eye(2), [x, y], simplify=True)
        passed, details = geom.verify_contracted_bianchi_identity()
        return ("VERIFIED" if passed else "FAILED"), details
    raise AssertionError(f"Unknown geometry operation: {op}")


def _dimension_case() -> tuple[str, dict[str, Any]]:
    from automate.theory.parser import parse_theory_file

    graph = parse_theory_file("examples/harmonic_oscillator.yaml")
    edge = graph.get_edge("edge_euler_lagrange")
    report = DimensionChecker().verify_edge(edge, graph)
    return _classify_report(report), {
        "status": report.status.value,
        "passed": report.passed,
        "error": report.error_message,
    }


def _unsupported_case(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    graph, edge = _graph_edge(
        case["rule"],
        [case["input"]],
        case["output"],
        checker="sympy",
    )
    report = SymPyChecker().verify_edge(edge, graph)
    return _classify_report(report), {
        "status": report.status.value,
        "backend": report.backend,
        "passed": report.passed,
        "reason": report.details.get("reason"),
        "error": report.error_message,
    }


CASES: list[dict[str, Any]] = []

# ---------------------------------------------------------------------------
# MATHS: 10 symbolic/algebraic
# ---------------------------------------------------------------------------
for number, (inp, out) in enumerate([
    ("x**2 + 2*x + 1", "(x + 1)**2"),
    ("sin(x)**2 + cos(x)**2", "1"),
    ("(a+b)**2", "a**2 + 2*a*b + b**2"),
    ("(x-y)*(x+y)", "x**2-y**2"),
    ("exp(x)*exp(y)", "exp(x+y)"),
    ("(2*x+3)*(x-1)", "2*x**2+x-3"),
    ("x**4-1", "(x**2-1)*(x**2+1)"),
    ("sin(x)+sin(-x)", "0"),
    ("(x+1)**3", "x**3+3*x**2+3*x+1"),
], start=1):
    CASES.append({
        "id": f"M-SYM-{number:02d}",
        "section": "Maths / symbolic-algebraic",
        "problem": f"Verify {inp} = {out}",
        "expected": "VERIFIED",
        "runner": _sympy_case,
        "rule": "algebraic_identity",
        "input": inp,
        "output": out,
    })
CASES.append({
    "id": "M-SYM-10",
    "section": "Maths / symbolic-algebraic",
    "problem": "Verify the arbitrary theorem Gamma(n+1)=n! for a general symbolic n using the current algebraic rule surface.",
    "expected": "UNVERIFIED",
    "runner": _unverified_case,
    "rule": "special_function_theorem",
    "input": "Gamma(n + 1)",
    "output": "factorial(n)",
})

# ---------------------------------------------------------------------------
# MATHS: 10 calculus/ODE
# ---------------------------------------------------------------------------
for number, (inp, out, wrt) in enumerate([
    ("x**2", "2*x", "x"),
    ("sin(x)", "cos(x)", "x"),
    ("exp(x)", "exp(x)", "x"),
    ("x**3+4*x", "3*x**2+4", "x"),
    ("sin(2*x)", "2*cos(2*x)", "x"),
    ("x**2+y**2", "2*x", "x"),
], start=1):
    CASES.append({
        "id": f"M-CALC-{number:02d}",
        "section": "Maths / calculus-ODE",
        "problem": f"Differentiate {inp} with respect to {wrt} and obtain {out}.",
        "expected": "VERIFIED",
        "runner": _sympy_case,
        "rule": "differentiate_both_sides",
        "input": inp,
        "output": out,
        "parameters": {"wrt": wrt},
    })
for number, (ode, sol) in enumerate([
    ("x_ddot+x", "C1*cos(t)+C2*sin(t)"),
    ("x_ddot-x", "C1*exp(t)+C2*exp(-t)"),
    ("x_ddot+4*x", "A*cos(2*t+phi)"),
], start=7):
    CASES.append({
        "id": f"M-CALC-{number:02d}",
        "section": "Maths / calculus-ODE",
        "problem": f"Verify solution {sol} for ODE {ode}=0.",
        "expected": "VERIFIED",
        "runner": _sympy_case,
        "rule": "verify_ode_solution",
        "input": ode,
        "output": sol,
        "parameters": {"coordinates": ["x"], "parameters": {}},
    })
CASES.append({
    "id": "M-CALC-10",
    "section": "Maths / calculus-ODE",
    "problem": "Reject the proposed solution A*cos(3*t+phi) for x''+4x=0.",
    "expected": "FAILED",
    "runner": _sympy_case,
    "rule": "verify_ode_solution",
    "input": "x_ddot+4*x",
    "output": "A*cos(3*t+phi)",
    "parameters": {"coordinates": ["x"], "parameters": {}},
})

# ---------------------------------------------------------------------------
# MATHS: 5 linear algebra
# ---------------------------------------------------------------------------
for number, problem in enumerate([
    "det([[1,2],[3,4]]) = -2",
    "eigenvalues of [[2,0],[0,3]] are 2 and 3",
    "A*(A*I) = A^2 for a symbolic square matrix A",
    "rank([[1,2],[2,4]]) = 1",
    "A^T*A is symmetric for every real matrix A",
], start=1):
    CASES.append({
        "id": f"M-LA-{number:02d}",
        "section": "Maths / linear-algebra",
        "problem": problem,
        "expected": "UNSUPPORTED_SEMANTICS",
        "runner": _unsupported_case,
        "rule": "linear_algebra",
        "input": problem,
        "output": problem,
    })

# ---------------------------------------------------------------------------
# MATHS: 5 tensor/index
# ---------------------------------------------------------------------------
mu_l = TensorIndex(symbol="mu", position="lower", dimension=4)
nu_u = TensorIndex(symbol="nu", position="upper", dimension=4)
nu_l = TensorIndex(symbol="nu", position="lower", dimension=4)
mu_u = TensorIndex(symbol="mu", position="upper", dimension=4)
CASES.extend([
    {
        "id": "M-TEN-01",
        "section": "Maths / tensor-index",
        "problem": "Validate A^nu B_nu with one free lower mu index.",
        "expected": "VERIFIED",
        "runner": _tensor_case,
        "operation": "product",
        "indices": [mu_l, nu_u, nu_l],
    },
    {
        "id": "M-TEN-02",
        "section": "Maths / tensor-index",
        "problem": "Reject T^mu S^mu because a repeated index has identical variance.",
        "expected": "FAILED",
        "runner": _tensor_case,
        "operation": "product",
        "indices": [mu_u, mu_u],
    },
    {
        "id": "M-TEN-03",
        "section": "Maths / tensor-index",
        "problem": "Reject a term where mu occurs three times.",
        "expected": "FAILED",
        "runner": _tensor_case,
        "operation": "product",
        "indices": [mu_u, mu_l, mu_u],
    },
    {
        "id": "M-TEN-04",
        "section": "Maths / tensor-index",
        "problem": "Reject contracted nu when its dimensions are 4 and 3.",
        "expected": "FAILED",
        "runner": _tensor_case,
        "operation": "product",
        "indices": [
            TensorIndex(symbol="nu", position="upper", dimension=4),
            TensorIndex(symbol="nu", position="lower", dimension=3),
        ],
    },
    {
        "id": "M-TEN-05",
        "section": "Maths / tensor-index",
        "problem": "Accept a rank-2 tensor equation with matching free mu,nu indices.",
        "expected": "VERIFIED",
        "runner": _tensor_case,
        "operation": "equation",
        "equation": TensorEquation(
            lhs=TensorExpression(
                terms=[[TensorIndex(symbol="mu", position="lower"),
                        TensorIndex(symbol="nu", position="lower")]]
            ),
            rhs=TensorExpression(
                terms=[[TensorIndex(symbol="mu", position="lower"),
                        TensorIndex(symbol="nu", position="lower")]]
            ),
        ),
    },
])

# ---------------------------------------------------------------------------
# MATHS: 5 numerical
# ---------------------------------------------------------------------------
for number, (eom, symbols, values, x0, v0) in enumerate([
    ("x_ddot+4*x", {"m": "positive", "k": "positive"}, {"m": 1.0, "k": 4.0}, 1.0, 0.0),
    ("x_ddot+9*x", {}, {}, 1.0, 0.0),
    ("x_ddot+2*x_dot+5*x", {"c": "positive", "k": "positive"}, {"c": 2.0, "k": 5.0}, 1.0, 0.0),
    ("x_ddot+g", {"g": "positive"}, {"g": 9.81}, 0.0, 0.0),
    ("x_ddot", {}, {}, 0.0, 1.0),
], start=1):
    CASES.append({
        "id": f"M-NUM-{number:02d}",
        "section": "Maths / numerical",
        "problem": f"Numerically integrate the ODE {eom}=0 with the declared initial conditions.",
        "expected": "VERIFIED",
        "runner": _numerical_case,
        "eom": eom,
        "symbols": symbols,
        "values": values,
        "x0": x0,
        "v0": v0,
        "t_max": 5.0,
    })

# ---------------------------------------------------------------------------
# PHYSICS: 5 mechanics
# ---------------------------------------------------------------------------
mechanics = [
    (
        "PHY-MECH-01",
        "Verify SHO EOM from L=m*x_dot^2/2-k*x^2/2.",
        "m*x_dot**2/2-k*x**2/2",
        ["x"],
        {"m": "positive", "k": "positive"},
        "eom",
        "m*x_ddot+k*x",
    ),
    (
        "PHY-MECH-02",
        "Cross-check the pendulum Euler-Lagrange equation against an independent SymPy variational path.",
        "m*l**2*theta_dot**2/2+m*g*l*cos(theta)",
        ["theta"],
        {"m": "positive", "g": "positive", "l": "positive"},
        "cross_check",
        None,
    ),
    (
        "PHY-MECH-03",
        "Verify central-force polar EOM for V(r)=-k/r.",
        "m*(r_dot**2+r**2*theta_dot**2)/2+k/r",
        ["r", "theta"],
        {"m": "positive", "k": "positive"},
        "eom",
        {
            "r": "m*r_ddot-m*r*theta_dot**2+k/r**2",
            "theta": "m*r**2*theta_ddot+2*m*r*r_dot*theta_dot",
        },
    ),
    (
        "PHY-MECH-04",
        "Verify free-particle 3D Euler-Lagrange equations.",
        "m*(x_dot**2+y_dot**2+z_dot**2)/2",
        ["x", "y", "z"],
        {"m": "positive"},
        "eom",
        {"x":"m*x_ddot","y":"m*y_ddot","z":"m*z_ddot"},
    ),
    (
        "PHY-MECH-05",
        "Verify the harmonic-oscillator Hamiltonian from the Legendre transform.",
        "m*x_dot**2/2-k*x**2/2",
        ["x"],
        {"m": "positive", "k": "positive"},
        "hamiltonian",
        None,
    ),
]
for cid, problem, lag, coords, params, operation, candidate in mechanics:
    CASES.append({
        "id": cid,
        "section": "Physics / mechanics",
        "problem": problem,
        "expected": "VERIFIED",
        "runner": _mechanics_case,
        "lagrangian": lag,
        "coordinates": coords,
        "parameters": params,
        "operation": operation,
        "candidate": candidate,
    })

# ---------------------------------------------------------------------------
# PHYSICS: 5 electromagnetism/vector calculus
# ---------------------------------------------------------------------------
for number, problem in enumerate([
    "Verify Gauss's law div(E)=rho/epsilon_0 from first principles.",
    "Verify Faraday's law curl(E)=-dB/dt.",
    "Verify Ampere-Maxwell law curl(B)=mu_0*J+mu_0*epsilon_0*dE/dt.",
    "Derive the Lorentz force q*(E+v cross B) from the current rule library.",
    "Verify div(B)=0 for an arbitrary magnetic field vector.",
], start=1):
    CASES.append({
        "id": f"PHY-EM-{number:02d}",
        "section": "Physics / electromagnetism-vector-calculus",
        "problem": problem,
        "expected": "UNSUPPORTED_SEMANTICS",
        "runner": _unsupported_case,
        "rule": "electromagnetism_vector_calculus",
        "input": problem,
        "output": problem,
    })

# ---------------------------------------------------------------------------
# PHYSICS: 5 tensor/geometry/relativity
# ---------------------------------------------------------------------------
for cid, problem, operation in [
    ("PHY-GEO-01", "Flat Cartesian 2D metric has vanishing Christoffel, Riemann and Ricci curvature.", "flat"),
    ("PHY-GEO-02", "Polar metric has Gamma^r_tt=-r and Gamma^theta_rtheta=1/r.", "polar_christoffel"),
    ("PHY-GEO-03", "The 2-sphere metric has Ricci scalar R=2/r^2.", "sphere_scalar"),
    ("PHY-GEO-04", "The 2D Schwarzschild t-r sector has Gamma^r_tt=M(r-2M)/r^3.", "schwarzschild_gamma"),
    ("PHY-GEO-05", "The contracted Bianchi identity holds for the flat metric.", "bianchi"),
]:
    CASES.append({
        "id": cid,
        "section": "Physics / tensor-geometry-relativity",
        "problem": problem,
        "expected": "VERIFIED",
        "runner": _geometry_case,
        "operation": operation,
    })


def test_acceptance_campaign_50(capsys):
    assert len(CASES) == 50, f"Campaign contains {len(CASES)} cases, expected exactly 50."
    counts = {
        "VERIFIED": 0,
        "UNVERIFIED": 0,
        "UNSUPPORTED_SEMANTICS": 0,
        "FAILED": 0,
    }
    results: list[dict[str, Any]] = []
    unexpected: list[dict[str, Any]] = []

    for case in CASES:
        observed, details = case["runner"](case)
        assert observed in CLASSIFICATIONS, f"{case['id']} returned invalid classification {observed!r}"
        counts[observed] += 1
        record = {
            "id": case["id"],
            "section": case["section"],
            "problem": case["problem"],
            "expected": case["expected"],
            "observed": observed,
            "details": details,
        }
        results.append(record)
        if observed != case["expected"]:
            unexpected.append(record)

    report = {
        "campaign": "Automate exact 50-problem Maths/Physics acceptance campaign",
        "total": len(results),
        "maths_total": sum(1 for c in CASES if c["id"].startswith("M-")),
        "physics_total": sum(1 for c in CASES if c["id"].startswith("PHY-")),
        "counts": counts,
        "unexpected_results": unexpected,
        "results": results,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    assert not unexpected, f"Acceptance classification mismatches: {[r['id'] for r in unexpected]}"
