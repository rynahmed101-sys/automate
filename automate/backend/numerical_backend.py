"""
NumericalChecker: Numerical computation and ODE simulation backend using NumPy, SciPy, and mpmath.
Validates mathematical equations of motion, trajectories, and conservation laws.
Stores algorithm, tolerances, versions, and reproducibility information.
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np
import scipy
import sympy as sp
from automate.backend.sympy_utils import safe_parse_expr
from scipy.integrate import solve_ivp

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph


class NumericalChecker(BaseChecker):
    def __init__(self, rtol: float = 1e-8, atol: float = 1e-10):
        self.rtol = rtol
        self.atol = atol

    @property
    def name(self) -> str:
        return "NumericalChecker"

    @property
    def version(self) -> str:
        return f"NumPy {np.__version__}, SciPy {scipy.__version__}"

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start_time = time.perf_counter()

        in_nodes = [graph.get_node(nid) for nid in edge.input_nodes]
        out_nodes = [graph.get_node(nid) for nid in edge.output_nodes]

        if not all(in_nodes) or not all(out_nodes):
            return VerificationReport(
                status=VerificationStatus.FAILED,
                backend=self.name,
                backend_version=self.version,
                passed=False,
                error_message="Referenced nodes missing from derivation graph."
            )

        rule = edge.transformation_rule
        passed = False
        error_msg = None
        details: Dict[str, Any] = {"rule": rule}
        certificates: List[Dict[str, Any]] = []

        try:
            supported_rules = {"numerical_simulation"}
            if rule not in supported_rules:
                raise ValueError(f"Unsupported numerical transformation rule: {rule}")

            passed, details, certificates, error_msg = self._simulate_harmonic_oscillator(
                in_nodes[0], edge.parameters
            )
        except Exception as e:
            passed = False
            error_msg = f"Numerical execution error: {type(e).__name__}: {str(e)}"

        elapsed = (time.perf_counter() - start_time) * 1000

        if passed:
            status = VerificationStatus.NUMERICALLY_CHECKED
            edge.status = status
            edge.checker = "numerical"
            edge.certificate = DerivationCertificate(
                rule_name=rule,
                steps=certificates,
                backend_version=self.version,
                execution_time_ms=elapsed,
                metrics=details.get("metrics", {})
            )
        else:
            status = VerificationStatus.FAILED
            edge.status = status
            edge.checker = "numerical"
            edge.failed_reason = error_msg

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations or [{"type": "ode_integration", "method": "RK45"}],
            command_invocation=f"solve_ivp(ode_sys, {edge.parameters})",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility=details.get("reproducibility", {}),
            metrics=details.get("metrics", {})
        )
        edge.evidence = evidence.to_dict()

        return VerificationReport(
            status=status,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=passed,
            details=details,
            error_message=error_msg,
            certificates=certificates,
            evidence=evidence
        )

    def _simulate_harmonic_oscillator(
        self, eom_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        m = float(params.get("m", 1.0))
        k = float(params.get("k", 4.0))

        raw_eom = eom_node.expression.raw_str.strip()
        if "=" not in raw_eom:
            return False, {}, [], "Numerical simulation requires an equality equation of motion."

        lhs_text, rhs_text = raw_eom.split("=", 1)
        q = sp.Symbol("x")
        q_ddot = sp.Symbol("x_ddot")
        local = {
            "x": q,
            "x_ddot": q_ddot,
            "m": sp.Float(m),
            "k": sp.Float(k),
        }
        try:
            eom_residual = sp.simplify(
                safe_parse_expr(lhs_text.strip(), locals_map=local)
                - safe_parse_expr(rhs_text.strip(), locals_map=local)
            )
        except Exception as exc:
            return False, {}, [], f"Could not parse equation of motion: {type(exc).__name__}: {exc}"

        expected_residual = m * q_ddot + k * q
        equivalent = eom_residual == expected_residual
        if not equivalent:
            try:
                ratio = sp.simplify(eom_residual / expected_residual)
                equivalent = bool(ratio.is_number and ratio != 0)
            except Exception:
                equivalent = False
        if not equivalent:
            return False, {
                "supplied_eom_residual": str(eom_residual),
                "expected_harmonic_residual": str(expected_residual),
            }, [], "Numerical backend only supports the harmonic oscillator equation m*x_ddot + k*x = 0."
        x0 = float(params.get("x0", 1.0))
        v0 = float(params.get("v0", 0.0))
        t_span = (0.0, float(params.get("t_max", 10.0)))
        t_eval = np.linspace(t_span[0], t_span[1], 500)

        if m <= 0 or k <= 0:
            return False, {}, [], "Physical parameters require m > 0 and k > 0."
        numeric_params = {"m": m, "k": k, "x0": x0, "v0": v0, "t_max": t_span[1]}
        if not all(np.isfinite(value) for value in numeric_params.values()):
            return False, {}, [], "Numerical parameters must all be finite."
        if t_span[1] <= 0:
            return False, {}, [], "t_max must be positive."

        omega = np.sqrt(k / m)

        def ode_sys(t, y):
            x, v = y
            return [v, -(k / m) * x]

        sol = solve_ivp(
            ode_sys,
            t_span,
            [x0, v0],
            t_eval=t_eval,
            method="RK45",
            rtol=self.rtol,
            atol=self.atol,
        )

        if not sol.success:
            return False, {}, [], f"ODE solver failed: {sol.message}"

        x_num, v_num, t = sol.y[0], sol.y[1], sol.t

        x_exact = x0 * np.cos(omega * t) + (v0 / omega) * np.sin(omega * t)
        v_exact = -x0 * omega * np.sin(omega * t) + v0 * np.cos(omega * t)

        x_abs_err = np.abs(x_num - x_exact)
        v_abs_err = np.abs(v_num - v_exact)
        max_abs_error = float(np.max(x_abs_err))
        velocity_max_abs_error = float(np.max(v_abs_err))
        rmse = float(np.sqrt(np.mean(x_abs_err**2)))
        velocity_rmse = float(np.sqrt(np.mean(v_abs_err**2)))

        E_num = 0.5 * m * v_num**2 + 0.5 * k * x_num**2
        E0 = 0.5 * m * v0**2 + 0.5 * k * x0**2
        absolute_energy_drift = float(np.max(np.abs(E_num - E0)))
        if E0 > 0:
            energy_drift = absolute_energy_drift / E0
            energy_drift_mode = "relative"
        else:
            energy_drift = absolute_energy_drift
            energy_drift_mode = "absolute_zero_initial_energy"

        max_allowed_error = 1e-4
        max_allowed_drift = 1e-4
        passed = (
            max_abs_error < max_allowed_error
            and velocity_max_abs_error < max_allowed_error
            and energy_drift < max_allowed_drift
        )

        metrics = {
            "max_abs_error": max_abs_error,
            "rmse": rmse,
            "velocity_max_abs_error": velocity_max_abs_error,
            "velocity_rmse": velocity_rmse,
            "energy_drift_relative": energy_drift if E0 > 0 else None,
            "energy_drift_absolute": absolute_energy_drift,
            "energy_drift_mode": energy_drift_mode,
            "initial_energy_joules": float(E0),
            "final_energy_joules": float(E_num[-1]),
            "num_steps": len(t),
            "solver_method": "RK45",
            "rtol": self.rtol,
            "atol": self.atol,
        }

        details = {
            "parameters": {"m": m, "k": k, "x0": x0, "v0": v0, "omega": omega},
            "metrics": metrics,
            "reproducibility": {
                "algorithm": "Explicit Runge-Kutta method of order 5(4) Dormand-Prince",
                "software": self.version,
                "t_span": list(t_span),
                "grid_points": 500,
            },
        }

        certificates = [
            {
                "step": "ivp_integration",
                "description": f"Solved m*d2x/dt2 + k*x = 0 over t in {t_span}",
                "result": f"RMSE = {rmse:.2e}, Max Error = {max_abs_error:.2e}",
            },
            {
                "step": "velocity_validation",
                "description": "Compared numerical velocity against the closed-form solution.",
                "result": f"RMSE = {velocity_rmse:.2e}, Max Error = {velocity_max_abs_error:.2e}",
            },
            {
                "step": "energy_conservation_check",
                "description": "Computed mechanical energy E(t) = 0.5*m*v^2 + 0.5*k*x^2",
                "result": (
                    f"Max {energy_drift_mode} drift = {energy_drift:.2e} "
                    f"(tolerance < {max_allowed_drift})"
                ),
            },
        ]

        error_msg = None if passed else (
            "Numerical tolerances exceeded: "
            f"x_max_err={max_abs_error:.2e}, "
            f"v_max_err={velocity_max_abs_error:.2e}, "
            f"energy_drift={energy_drift:.2e}"
        )
        return passed, details, certificates, error_msg
