"""
SymPyChecker: Symbolic mathematics backend using SymPy.
Verifies algebraic identities, differentiation, Euler-Lagrange equations,
differential equation solutions, and conservation laws.

All verifiers read their mathematical content from the graph's node expressions
and edge parameters. No hardcoded solutions are accepted. Unknown rules
return NOT_APPLICABLE rather than silently passing.
"""

import time
from typing import Dict, Any, List, Optional, Union
import sympy as sp

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph


class SymPyChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "SymPyChecker"

    @property
    def version(self) -> str:
        return sp.__version__

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

        # Check side conditions against active assumptions
        active_asms = {aid for aid, a in graph.assumptions.items() if a.active}
        cond_status = None
        if edge.side_conditions:
            valid_conds, missing_conds = edge.validate_side_conditions(active_asms)
            if not valid_conds:
                cond_status = VerificationStatus.CONDITIONAL
                error_msg = f"Missing or inactive required side condition(s): {', '.join(missing_conds)}"

        if cond_status == VerificationStatus.CONDITIONAL:
            passed = False
            status = VerificationStatus.CONDITIONAL
        else:
            try:
                if rule == "euler_lagrange":
                    passed, details, certificates, error_msg = self._verify_euler_lagrange(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "conserve_energy":
                    passed, details, certificates, error_msg = self._verify_energy_conservation(
                        in_nodes, out_nodes[0], edge.parameters
                    )
                elif rule == "solve_harmonic_oscillator":
                    passed, details, certificates, error_msg = self._verify_ode_solution(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "verify_ode_solution":
                    # Generic ODE verifier — same substitution logic, no SHO-specific assumptions
                    passed, details, certificates, error_msg = self._verify_ode_solution(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "algebraic_identity":
                    passed, details, certificates, error_msg = self._verify_algebraic_identity(
                        in_nodes[0], out_nodes[0]
                    )
                elif rule == "vary_action":
                    passed, details, certificates, error_msg = self._verify_field_equation(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "numerical_simulation":
                    # Numerical simulation: symbolic backend cannot verify this
                    status = VerificationStatus.NOT_APPLICABLE
                    details = {"rule": rule, "reason": "Numerical simulation requires numerical backend."}
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return self._build_report(status, passed, details, certificates, error_msg,
                                              edge, graph, elapsed)
                elif rule == "empirical_inference":
                    # Empirical inference: symbolic backend cannot verify this
                    status = VerificationStatus.NOT_APPLICABLE
                    details = {"rule": rule, "reason": "Empirical inference requires statistical backend."}
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return self._build_report(status, passed, details, certificates, error_msg,
                                              edge, graph, elapsed)
                else:
                    # NO FALLBACK — unknown rules must not be silently checked
                    # by algebraic identity. Return NOT_APPLICABLE explicitly.
                    status = VerificationStatus.NOT_APPLICABLE
                    details = {
                        "rule": rule,
                        "reason": (
                            f"Rule '{rule}' has no dedicated SymPy verifier and "
                            "no fallback is permitted. Register a dedicated rule or "
                            "use the correct checker. Unknown rules must not silently "
                            "pass algebraic identity checks."
                        ),
                    }
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return self._build_report(
                        status, False, details, [], None, edge, graph, elapsed
                    )
            except Exception as e:
                passed = False
                error_msg = f"SymPy computation error: {type(e).__name__}: {str(e)}"

            status = VerificationStatus.SYMBOLIC_CHECKED if passed else VerificationStatus.FAILED

        elapsed = (time.perf_counter() - start_time) * 1000
        return self._build_report(status, passed, details, certificates, error_msg,
                                  edge, graph, elapsed, rule=rule)

    # ------------------------------------------------------------------
    # Internal helper: build the final VerificationReport and update edge
    # ------------------------------------------------------------------
    def _build_report(
        self, status, passed, details, certificates, error_msg,
        edge, graph, elapsed, rule=None
    ) -> VerificationReport:
        rule = rule or edge.transformation_rule
        if passed and certificates:
            edge.certificate = DerivationCertificate(
                rule_name=rule,
                steps=certificates,
                backend_version=f"SymPy {self.version}",
                execution_time_ms=elapsed,
                metrics={"symbolic_zero_tested": True}
            )

        edge.status = status
        edge.checker = "sympy"
        if not passed:
            edge.failed_reason = error_msg

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations or [{"rule": rule, "target": "symbolic_equivalence"}],
            command_invocation=f"SymPyChecker.verify_edge('{edge.id}')",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility={"engine": "sympy", "version": self.version},
            metrics={"zero_tested": passed}
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

    # ------------------------------------------------------------------
    # Rule: euler_lagrange
    # Reads Lagrangian from in_nodes[0].expression.raw_str.
    # Reads coordinates and parameters from edge.parameters.
    # Returns UNSUPPORTED if coordinates are not provided.
    # ------------------------------------------------------------------
    def _verify_euler_lagrange(
        self, lagr_node: Any, eom_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        coords = params.get("coordinates")
        if not coords:
            return (
                False, {"rule": "euler_lagrange"},
                [],
                "UNSUPPORTED: edge.parameters['coordinates'] is required (e.g. ['x'] or ['r','theta']). "
                "Cannot infer coordinate without explicit specification."
            )

        sym_params = params.get("parameters", {})
        lagrangian_str = lagr_node.expression.raw_str
        candidate_eom_raw = eom_node.expression.raw_str

        try:
            from automate.mechanics.lagrangian import LagrangianSystem
            sys = LagrangianSystem(
                lagrangian=lagrangian_str,
                coordinates=coords,
                parameters=sym_params,
            )
            # candidate may be dict or single string
            if isinstance(candidate_eom_raw, dict):
                candidate = candidate_eom_raw
            else:
                candidate = candidate_eom_raw
            passed, details, steps, err = sys.verify_euler_lagrange(candidate)
        except Exception as e:
            return False, {"rule": "euler_lagrange", "lagrangian": lagrangian_str}, [], \
                f"LagrangianSystem error: {type(e).__name__}: {str(e)}"

        details.update({"lagrangian_input": lagrangian_str, "candidate_eom": candidate_eom_raw})
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: conserve_energy
    # Reads Lagrangian from in_nodes[0], candidate energy from out_node.
    # ------------------------------------------------------------------
    def _verify_energy_conservation(
        self, in_nodes: List[Any], energy_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        coords = params.get("coordinates")
        if not coords:
            return (
                False, {"rule": "conserve_energy"}, [],
                "UNSUPPORTED: edge.parameters['coordinates'] required for energy conservation check."
            )

        sym_params = params.get("parameters", {})
        lagrangian_str = in_nodes[0].expression.raw_str
        candidate_energy_str = energy_node.expression.raw_str

        try:
            from automate.mechanics.lagrangian import LagrangianSystem
            sys = LagrangianSystem(
                lagrangian=lagrangian_str,
                coordinates=coords,
                parameters=sym_params,
            )
            passed, details, steps, err = sys.verify_energy_conservation(candidate_energy_str)
        except Exception as e:
            return False, {"rule": "conserve_energy", "lagrangian": lagrangian_str}, [], \
                f"LagrangianSystem error: {type(e).__name__}: {str(e)}"

        details.update({"lagrangian_input": lagrangian_str, "candidate_energy": candidate_energy_str})
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: solve_harmonic_oscillator (generalised: ODE solution verifier)
    # Reads ODE from in_nodes[0], candidate solution from out_node.
    # Verifies by substituting candidate into ODE and checking residual == 0.
    # ------------------------------------------------------------------
    def _verify_ode_solution(
        self, ode_node: Any, sol_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        ode_str = ode_node.expression.raw_str
        sol_str = sol_node.expression.raw_str
        coords = params.get("coordinates", ["x"])
        sym_params = params.get("parameters", {})
        q0 = coords[0]

        t = sp.Symbol("t", real=True)

        # Build parameter symbols
        param_syms: Dict[str, sp.Expr] = {}
        for p_name, p_props in sym_params.items():
            if p_props == "positive":
                param_syms[p_name] = sp.Symbol(p_name, positive=True, real=True)
            else:
                param_syms[p_name] = sp.Symbol(p_name, real=True)

        # Common free symbols in candidate solutions
        aux_syms: Dict[str, sp.Expr] = {}
        for name in ["A", "phi", "omega", "C1", "C2", "B"]:
            if name not in param_syms:
                aux_syms[name] = sp.Symbol(name, real=True)

        # ---- Detect ODE notation style ----
        # Shorthand mode: ODE uses x_ddot, x_dot, x  (bare symbols, no x(t))
        # Function mode: ODE uses x(t), diff(x(t),t,2)
        uses_function_notation = f"{q0}(t)" in ode_str or "diff(" in ode_str

        q0_func = sp.Function(q0)(t)   # x(t) — applied function

        if uses_function_notation:
            # Map "x" → Function class so "x(t)" in string → Function("x")(t)
            fn_local: Dict[str, Any] = {"t": t, "diff": sp.diff, **param_syms, **aux_syms}
            fn_local[q0] = sp.Function(q0)           # unapplied class
            fn_local[f"{q0}_dot"] = sp.diff(q0_func, t)
            fn_local[f"{q0}_ddot"] = sp.diff(q0_func, t, 2)
            ode_syms = fn_local
            # The applied function is what we substitute
            q0_sym_in_ode = q0_func
        else:
            # Map "x" → bare Symbol for shorthand notation
            q0_bare = sp.Symbol(q0, real=True)
            sh_local: Dict[str, Any] = {
                "t": t,
                q0: q0_bare,
                f"{q0}_dot": sp.Symbol(f"{q0}_dot", real=True),
                f"{q0}_ddot": sp.Symbol(f"{q0}_ddot", real=True),
                **param_syms,
                **aux_syms,
            }
            ode_syms = sh_local
            q0_sym_in_ode = q0_bare    # bare symbol to substitute in ODE

        # Solution is always parsed as an expression in t (and parameters)
        # The solution string may be "x(t) = A*cos(...)" or just "A*cos(...)"
        sol_local: Dict[str, Any] = {"t": t, **param_syms, **aux_syms, "sqrt": sp.sqrt, "cos": sp.cos, "sin": sp.sin, "exp": sp.exp}

        actual_sol_str = sol_str.strip()
        if "=" in actual_sol_str:
            lhs_s, rhs_s = actual_sol_str.split("=", 1)
            lhs_s = lhs_s.strip()
            if lhs_s in (f"{q0}(t)", q0, f"{q0}(t, )"):
                actual_sol_str = rhs_s.strip()
            else:
                actual_sol_str = rhs_s.strip()

        try:
            sol_expr = sp.sympify(actual_sol_str, locals=sol_local)
        except Exception as e:
            return False, {"rule": "solve_ode", "ode": ode_str, "solution": sol_str}, [], \
                f"Candidate solution parse error: {type(e).__name__}: {str(e)}"

        # Parse the ODE expression
        try:
            if "=" in ode_str:
                parts = ode_str.split("=", 1)
                ode_lhs = sp.sympify(parts[0].strip(), locals=ode_syms)
                ode_rhs = sp.sympify(parts[1].strip(), locals=ode_syms)
                ode_expr = ode_lhs - ode_rhs
            else:
                ode_expr = sp.sympify(ode_str, locals=ode_syms)
        except Exception as e:
            return False, {"rule": "solve_ode", "ode": ode_str, "solution": sol_str}, [], \
                f"ODE parse error: {type(e).__name__}: {str(e)}"

        steps = [{"step": 1, "operation": "candidate_solution", "parsed": str(sol_expr),
                  "notation": "function" if uses_function_notation else "shorthand"}]

        # For shorthand ODEs, need to also substitute derivatives.
        # Compute d/dt(sol_expr) and d²/dt²(sol_expr) for x_dot and x_ddot substitution.
        subs_map: Dict[sp.Expr, sp.Expr] = {}
        if uses_function_notation:
            subs_map[q0_func] = sol_expr
        else:
            q0_sym = ode_syms[q0]
            q0_dot_sym = ode_syms.get(f"{q0}_dot")
            q0_ddot_sym = ode_syms.get(f"{q0}_ddot")
            subs_map[q0_sym] = sol_expr
            if q0_dot_sym is not None:
                try:
                    subs_map[q0_dot_sym] = sp.diff(sol_expr, t)
                except Exception:
                    pass
            if q0_ddot_sym is not None:
                try:
                    subs_map[q0_ddot_sym] = sp.diff(sol_expr, t, 2)
                except Exception:
                    pass

        try:
            substituted = ode_expr.subs(subs_map)
            residual = sp.simplify(substituted)
        except Exception as e:
            return False, {"rule": "solve_ode", "ode": ode_str}, [], \
                f"Substitution error: {type(e).__name__}: {str(e)}"

        steps.append({"step": 2, "operation": "ode_residual_after_substitution", "expr": str(residual)})

        # Substitute parameter aliases (e.g. omega = sqrt(k/m)) before zero-test
        alias_subs: Dict[sp.Expr, sp.Expr] = {}
        for p_key, p_val in params.items():
            if p_key in ("coordinates", "parameters", "numerical_parameters",
                         "initial_conditions", "initial_velocities", "t_max"):
                continue
            if isinstance(p_val, str) and p_val.strip():
                try:
                    alias_sym = aux_syms.get(p_key) or param_syms.get(p_key) or sp.Symbol(p_key, real=True)
                    alias_expr_parsed = sp.sympify(p_val.strip(), locals={**param_syms, **aux_syms, "t": t, "sqrt": sp.sqrt})
                    if isinstance(alias_sym, sp.Symbol):
                        alias_subs[alias_sym] = alias_expr_parsed
                except Exception:
                    pass

        if alias_subs and residual != 0:
            try:
                residual = sp.simplify(residual.subs(alias_subs))
            except Exception:
                pass
            steps.append({"step": 3, "operation": "residual_after_alias_substitution",
                          "aliases": {str(k): str(v) for k, v in alias_subs.items()},
                          "expr": str(residual)})

        passed = (residual == 0)
        details = {
            "ode": ode_str,
            "candidate_solution": sol_str,
            "parsed_solution": str(sol_expr),
            "notation_mode": "function" if uses_function_notation else "shorthand",
            "alias_substitutions": {str(k): str(v) for k, v in alias_subs.items()},
            "residual": str(residual),
            "satisfies_ode": passed,
        }
        err = None if passed else f"ODE solution residual is non-zero: {residual}"
        return passed, details, steps, err


    # ------------------------------------------------------------------
    # Rule: vary_action
    # Reads Lagrangian density from in_nodes[0], field equations from out_node.
    # Uses FieldTheoryAction engine.
    # ------------------------------------------------------------------
    def _verify_field_equation(
        self, action_node: Any, feq_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        fields = params.get("fields")
        if not fields:
            return (
                False, {"rule": "vary_action"}, [],
                "UNSUPPORTED: edge.parameters['fields'] required for vary_action rule."
            )

        coords = params.get("coordinates")
        sym_params = params.get("parameters", {})
        lagrangian_density_str = action_node.expression.raw_str
        candidate_feq_str = feq_node.expression.raw_str

        try:
            from automate.field_theory.variational import FieldTheoryAction
            action = FieldTheoryAction(
                lagrangian_density=lagrangian_density_str,
                fields=fields,
                coordinates=coords,
                parameters=sym_params,
            )
            passed, details, steps, err = action.verify_field_equation(candidate_feq_str)
        except Exception as e:
            return False, {"rule": "vary_action", "lagrangian_density": lagrangian_density_str}, [], \
                f"FieldTheoryAction error: {type(e).__name__}: {str(e)}"

        details.update({
            "lagrangian_density_input": lagrangian_density_str,
            "candidate_field_equation": candidate_feq_str
        })
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: algebraic_identity
    # Uses SafeParser — no bare sympify.
    # ------------------------------------------------------------------
    def _verify_algebraic_identity(
        self, in_node: Any, out_node: Any
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        parser = SafeParser()
        try:
            expr1 = parser.parse(in_node.expression.raw_str)
            expr2 = parser.parse(out_node.expression.raw_str)
        except SafeParseError as e:
            return False, {"rule": "algebraic_identity"}, [], \
                f"SafeParser rejected expression: {e}"
        diff = sp.simplify(expr1 - expr2)
        passed = (diff == 0)
        details = {"diff": str(diff), "equal": passed}
        steps = [{"step": 1, "operation": "simplify(expr1 - expr2)", "expr": str(diff)}]
        err = None if passed else f"Expressions are not algebraically identical: {diff}"
        return passed, details, steps, err



# Type alias used in type hints above
Any = object
