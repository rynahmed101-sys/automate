"""
NumericalChecker: Numerical computation and ODE simulation backend using NumPy, SciPy.

This backend reads the ODE system from the graph's node expressions and edge parameters.
It does NOT hardcode any specific physical system. If the rule is not ODE-type or the
required parameters are missing, it returns UNSUPPORTED rather than silently falling back
to a harmonic oscillator simulation.

Supported rules with ODE integration:
  - euler_lagrange       : integrates EoM extracted from coordinates + params
  - solve_harmonic_oscillator : integrates EoM string from in_node expression
  - conserve_energy      : checks energy conservation numerically along integrated trajectory
  - numerical_simulation : general ODE simulation using in_node expression as EoM string

Unsupported rules return NOT_APPLICABLE.
"""

import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import sympy as sp
import scipy
from scipy.integrate import solve_ivp

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph

# Rules that involve ODE integration
_ODE_RULES = frozenset({
    "euler_lagrange",
    "solve_harmonic_oscillator",
    "conserve_energy",
    "numerical_simulation",
})


class NumericalChecker(BaseChecker):
    def __init__(
        self,
        rtol: float = 1e-8,
        atol: float = 1e-10,
        convergence_tolerance: float = 1e-6,
        refinement_factor: float = 10.0,
    ):
        if not (0 < rtol < 1):
            raise ValueError("rtol must be in (0, 1).")
        if not (0 < atol < 1):
            raise ValueError("atol must be in (0, 1).")
        if not (convergence_tolerance > 0):
            raise ValueError("convergence_tolerance must be positive.")
        if not (refinement_factor > 1):
            raise ValueError("refinement_factor must be > 1.")
        self.rtol = rtol
        self.atol = atol
        self.convergence_tolerance = convergence_tolerance
        self.refinement_factor = refinement_factor

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

        if rule not in _ODE_RULES:
            # This backend cannot verify non-ODE rules
            status = VerificationStatus.NOT_APPLICABLE
            details["reason"] = (
                f"Rule '{rule}' does not involve ODE integration; "
                "numerical backend is not applicable."
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            return self._build_report(
                status, False, details, [], None, edge, graph, elapsed
            )

        try:
            passed, details, certificates, error_msg = self._simulate_ode_from_graph(
                rule, in_nodes, out_nodes, edge.parameters
            )
        except Exception as e:
            passed = False
            error_msg = f"Numerical execution error: {type(e).__name__}: {str(e)}"

        elapsed = (time.perf_counter() - start_time) * 1000
        status = VerificationStatus.NUMERICALLY_CHECKED if passed else VerificationStatus.FAILED
        return self._build_report(status, passed, details, certificates, error_msg, edge, graph, elapsed)

    def _build_report(
        self, status, passed, details, certificates, error_msg, edge, graph, elapsed
    ) -> VerificationReport:
        rule = edge.transformation_rule

        fingerprint = self._claim_fingerprint(edge, graph, [graph.get_node(nid) for nid in edge.input_nodes], [graph.get_node(nid) for nid in edge.output_nodes])
        details.setdefault("reproducibility", {})["claim_fingerprint_sha256"] = fingerprint
        details.setdefault("metrics", {})["claim_fingerprint_sha256"] = fingerprint

        if passed:
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
            edge.status = status
            edge.checker = "numerical"
            if error_msg:
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

    def _claim_fingerprint(
        self,
        edge: DerivationEdge,
        graph: DerivationGraph,
        in_nodes: list,
        out_nodes: list,
    ) -> str:
        """Hash the graph claim and numerical configuration for provenance."""
        payload = {
            "graph_id": getattr(graph, "id", None),
            "edge_id": edge.id,
            "rule": edge.transformation_rule,
            "input_nodes": [
                {"id": n.id, "expression": n.expression.raw_str}
                for n in in_nodes
            ],
            "output_nodes": [
                {"id": n.id, "expression": n.expression.raw_str}
                for n in out_nodes
            ],
            "parameters": edge.parameters,
        }
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _convergence_probe(
        self,
        ode_sys,
        t_span: Tuple[float, float],
        y0: list,
        t_eval: np.ndarray,
        fine_result,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Compare the accepted solve against a deliberately coarser tolerance run.

        This is empirical convergence evidence, not a rigorous global error bound.
        The run must remain close under tolerance refinement before it is reported
        as NUMERICALLY_CHECKED.
        """
        coarse_rtol = min(self.rtol * self.refinement_factor, 1e-2)
        coarse_atol = min(self.atol * self.refinement_factor, 1e-4)

        try:
            coarse_result = solve_ivp(
                ode_sys,
                t_span,
                y0,
                t_eval=t_eval,
                method="RK45",
                rtol=coarse_rtol,
                atol=coarse_atol,
            )
        except Exception as exc:
            return False, {
                "convergence_probe": "failed",
                "fine_rtol": self.rtol,
                "fine_atol": self.atol,
                "coarse_rtol": coarse_rtol,
                "coarse_atol": coarse_atol,
            }, f"Convergence probe execution failed: {type(exc).__name__}: {exc}"

        if not coarse_result.success:
            return False, {
                "convergence_probe": "failed",
                "fine_rtol": self.rtol,
                "fine_atol": self.atol,
                "coarse_rtol": coarse_rtol,
                "coarse_atol": coarse_atol,
                "coarse_solver_message": coarse_result.message,
            }, f"Convergence probe solver failed: {coarse_result.message}"

        if coarse_result.y.shape != fine_result.y.shape:
            return False, {
                "convergence_probe": "failed",
                "shape_fine": list(fine_result.y.shape),
                "shape_coarse": list(coarse_result.y.shape),
            }, "Convergence probe returned incompatible trajectory shapes."

        delta = np.abs(fine_result.y - coarse_result.y)
        state_scale = np.maximum(np.max(np.abs(fine_result.y), axis=1), 1.0)
        normalized = delta / state_scale[:, None]
        max_abs = float(np.max(delta))
        max_relative = float(np.max(normalized))
        passed = max_relative <= self.convergence_tolerance

        details = {
            "convergence_probe": "passed" if passed else "failed",
            "fine_rtol": self.rtol,
            "fine_atol": self.atol,
            "coarse_rtol": coarse_rtol,
            "coarse_atol": coarse_atol,
            "refinement_factor": self.refinement_factor,
            "max_abs_state_difference": max_abs,
            "max_relative_state_difference": max_relative,
            "convergence_tolerance": self.convergence_tolerance,
            "fine_internal_steps": int(getattr(fine_result, "nfev", 0)),
            "coarse_internal_steps": int(getattr(coarse_result, "nfev", 0)),
        }
        if passed:
            return True, details, None

        return False, details, (
            "Numerical result did not remain stable under tolerance refinement: "
            f"max relative state difference {max_relative:.2e} exceeds "
            f"convergence tolerance {self.convergence_tolerance:.2e}."
        )

    # ------------------------------------------------------------------
    # General ODE extractor and simulator.
    # Reads EoM from graph nodes and edge.parameters.
    # Never defaults to harmonic oscillator if the graph describes something else.
    # ------------------------------------------------------------------
    def _simulate_ode_from_graph(
        self,
        rule: str,
        in_nodes: list,
        out_nodes: list,
        params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Extracts an ODE system from the graph and integrates it.

        Strategy:
        1. Try to use LagrangianSystem (euler_lagrange / conserve_energy rules):
           requires 'coordinates' in edge.parameters.
        2. Fall back to parsing in_node[0].expression.raw_str as an ODE string
           (for numerical_simulation / solve_harmonic_oscillator).
        3. If neither is possible, return UNSUPPORTED.
        """
        coords = params.get("coordinates")
        sym_params = params.get("parameters", {})
        num_params = params.get("numerical_parameters", {})  # float values

        # Common integration parameters
        x0_map = params.get("initial_conditions", {})     # {coord: value}
        v0_map = params.get("initial_velocities", {})     # {coord: value}
        t_max = float(params.get("t_max", 10.0))
        t_span = (0.0, t_max)
        t_eval = np.linspace(0.0, t_max, 500)

        # ------------------------------------------------------------------
        # Path A: LagrangianSystem-based (requires coordinates)
        # ------------------------------------------------------------------
        if coords and rule in ("euler_lagrange", "conserve_energy"):
            lagrangian_str = in_nodes[0].expression.raw_str
            return self._integrate_lagrangian_system(
                lagrangian_str, coords, sym_params, num_params,
                x0_map, v0_map, t_span, t_eval, rule
            )

        # ------------------------------------------------------------------
        # Path B: Parse EoM string from in_node expression
        # ------------------------------------------------------------------
        eom_str = in_nodes[0].expression.raw_str
        if not eom_str or eom_str.strip() == "":
            return (
                False, {"rule": rule}, [],
                "UNSUPPORTED: No EoM expression found in input node and no coordinates provided."
            )

        return self._integrate_eom_string(
            eom_str, coords or ["x"], sym_params, num_params,
            x0_map, v0_map, t_span, t_eval, rule
        )

    def _integrate_lagrangian_system(
        self,
        lagrangian_str: str,
        coords: List[str],
        sym_params: Dict[str, Any],
        num_params: Dict[str, float],
        x0_map: Dict[str, float],
        v0_map: Dict[str, float],
        t_span: Tuple[float, float],
        t_eval: np.ndarray,
        rule: str
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """Derive EoMs via LagrangianSystem and integrate numerically."""
        try:
            from automate.mechanics.lagrangian import LagrangianSystem
            sys = LagrangianSystem(
                lagrangian=lagrangian_str,
                coordinates=coords,
                parameters=sym_params,
            )
            eoms, _ = sys.euler_lagrange_equations()
        except Exception as e:
            return False, {"lagrangian": lagrangian_str}, [], \
                f"Failed to derive EoMs from Lagrangian: {type(e).__name__}: {str(e)}"

        # Build lambdified ODE functions.
        # Solve each eom[q] == 0 for q_ddot symbolically.
        param_subs = {}
        for p_name in sym_params:
            val = num_params.get(p_name) or sym_params.get(p_name)
            if isinstance(val, (int, float)):
                param_subs[sys.symbols[p_name]] = float(val)

        accel_exprs = {}
        for q in coords:
            try:
                sol = sp.solve(eoms[q], sys.q_ddots[q])
                if not sol:
                    return False, {}, [], \
                        f"Cannot solve EoM for acceleration of '{q}' — system may be implicit."
                accel_exprs[q] = sol[0].subs(param_subs)
            except Exception as e:
                return False, {}, [], \
                    f"EoM solve error for '{q}': {type(e).__name__}: {str(e)}"

        # Build state vector: [q1, dq1/dt, q2, dq2/dt, ...]
        # Lambdify each acceleration expression
        state_syms = []
        q_idx = {}
        v_idx = {}
        for i, q in enumerate(coords):
            state_syms.append(sys.q_funcs[q])
            state_syms.append(sys.q_dots[q])
            q_idx[q] = 2 * i
            v_idx[q] = 2 * i + 1

        # After param substitution, remaining free symbols are q(t) and diff(q(t), t)
        accel_funcs = {}
        for q in coords:
            try:
                # Replace q(t) and dq/dt with state symbols for lambdify
                expr = accel_exprs[q]
                # Map q(t) and q_dot(t) to ordinary symbols for lambdify
                lam_subs = {}
                lam_syms = []
                lam_names = []
                for qn in coords:
                    pos_sym = sp.Symbol(f"_q_{qn}")
                    vel_sym = sp.Symbol(f"_v_{qn}")
                    lam_subs[sys.q_funcs[qn]] = pos_sym
                    lam_subs[sys.q_dots[qn]] = vel_sym
                    lam_syms.extend([pos_sym, vel_sym])
                    lam_names.extend([f"_q_{qn}", f"_v_{qn}"])

                expr_lam = expr.subs(lam_subs)
                f = sp.lambdify(lam_syms, expr_lam, modules="numpy")
                accel_funcs[q] = (f, lam_names)
            except Exception as e:
                return False, {}, [], \
                    f"Lambdify error for '{q}': {type(e).__name__}: {str(e)}"

        # Build initial conditions vector
        y0 = []
        for q in coords:
            y0.append(float(x0_map.get(q, 1.0)))
            y0.append(float(v0_map.get(q, 0.0)))

        def ode_sys(t, y):
            dy = []
            args = list(y)  # [q1, v1, q2, v2, ...]
            for i, q in enumerate(coords):
                v = y[v_idx[q]]
                dy.append(v)           # dq/dt = v
                f, _ = accel_funcs[q]
                a = float(f(*args))    # d²q/dt² = accel
                dy.append(a)
            return dy

        sol = solve_ivp(
            ode_sys, t_span, y0, t_eval=t_eval,
            method="RK45", rtol=self.rtol, atol=self.atol
        )

        if not sol.success:
            return False, {"lagrangian": lagrangian_str}, [], \
                f"ODE solver failed: {sol.message}"

        convergence_passed, convergence_metrics, convergence_error = self._convergence_probe(
            ode_sys, t_span, y0, t_eval, sol
        )

        conservation_passed, energy_drift = self._check_energy_conservation_numerical(
            sol, coords, sys, param_subs, x0_map, v0_map, num_params
        )

        if rule == "conserve_energy":
            if energy_drift is None:
                passed = False
                energy_error = (
                    "Energy conservation could not be evaluated; numerical backend "
                    "will not treat an unavailable diagnostic as success."
                )
            else:
                passed = conservation_passed
                energy_error = None
        else:
            passed = convergence_passed
            energy_error = None

        if not convergence_passed:
            passed = False

        metrics = {
            "num_steps": len(sol.t),
            "solver_method": "RK45",
            "rtol": self.rtol,
            "atol": self.atol,
            "energy_drift_relative": energy_drift if energy_drift is not None else "N/A",
            **convergence_metrics,
        }
        details = {
            "lagrangian": lagrangian_str,
            "coordinates": coords,
            "initial_conditions": {**x0_map, **v0_map},
            "t_span": list(t_span),
            "metrics": metrics,
            "reproducibility": {
                "algorithm": "Explicit Runge-Kutta method of order 5(4) Dormand-Prince",
                "software": self.version,
                "t_span": list(t_span),
                "grid_points": len(t_eval)
            }
        }

        certificates = [
            {
                "step": "lagrangian_ode_integration",
                "description": f"Integrated {len(coords)}-coordinate EoM over t in {t_span}",
                "result": f"Solver success: {sol.success}, steps: {len(sol.t)}"
            }
        ]
        certificates.append({
            "step": "tolerance_refinement_check",
            "description": "Compared accepted trajectory with a coarser RK45 tolerance run.",
            "result": (
                "Stable under refinement"
                if convergence_passed
                else "Unstable under refinement"
            ),
        })
        if energy_drift is not None:
            certificates.append({
                "step": "energy_conservation_check",
                "description": "Computed mechanical energy along trajectory",
                "result": f"Max relative drift = {energy_drift:.2e}"
            })

        max_drift_threshold = 1e-4
        if rule == "conserve_energy" and energy_drift is not None and energy_drift >= max_drift_threshold:
            error_msg = f"Energy not conserved: max relative drift = {energy_drift:.2e} (threshold {max_drift_threshold})"
        elif energy_error:
            error_msg = energy_error
        elif convergence_error:
            error_msg = convergence_error
        else:
            error_msg = None

        return passed, details, certificates, error_msg

    def _check_energy_conservation_numerical(
        self, sol, coords, sys, param_subs, x0_map, v0_map, num_params
    ):
        """Compute E(t) numerically and return (passed, max_relative_drift)."""
        try:
            # Construct Hamiltonian symbolically and lambdify
            H, p_syms = sys.hamiltonian()
            H_subs = H.subs(param_subs)

            # Map momenta to velocity expressions
            # For standard kinetic Lagrangians p_i = m * v_i;
            # we use numerical derivatives from sol.y
            v_idx = {q: 2 * i + 1 for i, q in enumerate(coords)}
            q_idx = {q: 2 * i for i, q in enumerate(coords)}

            # Build simple kinetic+potential energy from sol data
            # We re-use LagrangianSystem.canonical_momenta to build E
            momenta = sys.canonical_momenta()

            # Lambdify each momentum expression
            lam_subs_map = {}
            lam_syms_list = []
            for q in coords:
                ps = sp.Symbol(f"_q_{q}")
                vs = sp.Symbol(f"_v_{q}")
                lam_subs_map[sys.q_funcs[q]] = ps
                lam_subs_map[sys.q_dots[q]] = vs
                lam_syms_list.extend([ps, vs])

            E_expr = sum(
                momenta[q] * sys.q_dots[q] for q in coords
            ) - sys.lagrangian
            E_expr_subs = E_expr.subs(param_subs).subs(lam_subs_map)
            E_func = sp.lambdify(lam_syms_list, E_expr_subs, modules="numpy")

            args = [sol.y[v_idx[q] if i % 2 == 1 else q_idx[coords[i // 2]]]
                    for i in range(len(lam_syms_list))]
            # simpler approach: just pass all state components
            all_states = list(sol.y)  # shape (2*n_coords, n_steps)
            E_num = E_func(*all_states)
            E0 = float(E_num[0]) if hasattr(E_num, "__len__") else float(E_num)
            if abs(E0) < 1e-12:
                return True, 0.0
            drift = float(np.max(np.abs(E_num - E0))) / abs(E0)
            passed = drift < 1e-4
            return passed, drift
        except Exception:
            return False, None  # Unavailable evidence is not a successful check

    def _integrate_eom_string(
        self,
        eom_str: str,
        coords: List[str],
        sym_params: Dict[str, Any],
        num_params: Dict[str, float],
        x0_map: Dict[str, float],
        v0_map: Dict[str, float],
        t_span: Tuple[float, float],
        t_eval: np.ndarray,
        rule: str
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Parse the EoM expression string and integrate numerically.
        The EoM must be written as 'expression = 0' or just 'expression'
        that equals 0, in terms of q, q_dot, q_ddot (for first coord).
        """
        q_name = coords[0]
        t_sym = sp.Symbol("t", real=True)
        q_func = sp.Function(q_name)(t_sym)
        q_dot = sp.diff(q_func, t_sym)
        q_ddot = sp.diff(q_dot, t_sym)

        local_syms: Dict[str, Any] = {
            "t": t_sym,
            q_name: q_func,
            f"{q_name}_dot": q_dot,
            f"{q_name}_ddot": q_ddot,
        }
        for p_name, p_props in sym_params.items():
            if p_props == "positive":
                local_syms[p_name] = sp.Symbol(p_name, positive=True, real=True)
            else:
                local_syms[p_name] = sp.Symbol(p_name, real=True)

        try:
            from automate.ir.safe_parser import SafeParser, SafeParseError
            parser = SafeParser(extra_symbols=local_syms)
            if "=" in eom_str:
                eom_expr = parser.parse_equation(eom_str)
            else:
                eom_expr = parser.parse(eom_str)
        except SafeParseError as e:
            return False, {"eom": eom_str}, [], f"SafeParser rejected EoM expression: {e}"
        except Exception as e:
            return False, {"eom": eom_str}, [], \
                f"EoM string parse error: {type(e).__name__}: {str(e)}"

        # Substitute numerical parameter values
        param_subs = {}
        for p_name in sym_params:
            val = num_params.get(p_name)
            if val is not None:
                param_subs[local_syms[p_name]] = float(val)
        eom_expr = eom_expr.subs(param_subs)

        # Solve for q_ddot
        try:
            sol_accel = sp.solve(eom_expr, q_ddot)
            if not sol_accel:
                return False, {"eom": eom_str}, [], \
                    "Cannot solve EoM for acceleration; equation may be implicit."
            accel_expr = sol_accel[0]
        except Exception as e:
            return False, {"eom": eom_str}, [], \
                f"Cannot solve EoM for acceleration: {type(e).__name__}: {str(e)}"

        # Lambdify: accel(q, v)
        q_s = sp.Symbol("_q", real=True)
        v_s = sp.Symbol("_v", real=True)
        accel_lam_expr = accel_expr.subs({q_func: q_s, q_dot: v_s})
        try:
            accel_func = sp.lambdify([q_s, v_s], accel_lam_expr, modules="numpy")
        except Exception as e:
            return False, {"eom": eom_str}, [], \
                f"Lambdify error: {type(e).__name__}: {str(e)}"

        x0 = float(x0_map.get(q_name, 1.0))
        v0 = float(v0_map.get(q_name, 0.0))

        def ode_sys(t, y):
            q_val, v_val = y
            return [v_val, float(accel_func(q_val, v_val))]

        y0 = [x0, v0]
        result = solve_ivp(
            ode_sys, t_span, y0, t_eval=t_eval,
            method="RK45", rtol=self.rtol, atol=self.atol
        )

        if not result.success:
            return False, {"eom": eom_str}, [], \
                f"ODE solver failed: {result.message}"

        convergence_passed, convergence_metrics, convergence_error = self._convergence_probe(
            ode_sys, t_span, y0, t_eval, result
        )

        metrics = {
            "num_steps": len(result.t),
            "solver_method": "RK45",
            "rtol": self.rtol,
            "atol": self.atol,
            **convergence_metrics,
        }
        details = {
            "eom_string": eom_str,
            "accel_expr": str(accel_expr),
            "initial_conditions": {q_name: x0, f"{q_name}_dot": v0},
            "t_span": list(t_span),
            "metrics": metrics,
            "reproducibility": {
                "algorithm": "Explicit Runge-Kutta method of order 5(4) Dormand-Prince",
                "software": self.version,
                "t_span": list(t_span),
                "grid_points": len(t_eval)
            }
        }
        certificates = [{
            "step": "eom_string_integration",
            "description": f"Integrated EoM '{eom_str}' over t in {t_span}",
            "result": f"Solver success: {result.success}, steps: {len(result.t)}"
        }, {
            "step": "tolerance_refinement_check",
            "description": "Compared accepted trajectory with a coarser RK45 tolerance run.",
            "result": (
                "Stable under refinement"
                if convergence_passed
                else "Unstable under refinement"
            ),
        }]

        if convergence_error:
            return False, details, certificates, convergence_error

        return True, details, certificates, None
