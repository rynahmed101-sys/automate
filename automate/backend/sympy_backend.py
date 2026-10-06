"""
SymPyChecker: Symbolic mathematics backend using SymPy.
Verifies algebraic identities, differentiation, Euler-Lagrange equations,
differential equation solutions, and conservation laws.

All verifiers read their mathematical content from the graph's node expressions
and edge parameters. No hardcoded solutions are accepted. Unknown rules
return NOT_APPLICABLE rather than silently passing.
"""

import time
import re
from typing import Dict, Any, List, Optional, Union
import sympy as sp
import numpy as np

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph
from automate.ode import ODEEngine


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
                elif rule in {
                    "solve_harmonic_oscillator",
                    "verify_ode_solution",
                    "solve_separable_ode",
                    "solve_linear_first_order_ode",
                    "solve_bernoulli_ode",
                    "solve_exact_ode",
                    "solve_constant_coefficient_ode",
                    "verify_ode_ivp",
                    "verify_ode_bvp",
                    "verify_ode_system",
                    "ode_phase_space",
                }:
                    passed, details, certificates, error_msg, status_override = self._verify_ode_rule(
                        rule, in_nodes, out_nodes, edge.parameters
                    )
                    details["_status_override"] = status_override.value
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
                elif rule == "divide_both_sides":
                    passed, details, certificates, error_msg = self._verify_divide_both_sides(
                        in_nodes[0], out_nodes[0], edge.parameters, graph, edge.side_conditions
                    )
                elif rule == "differentiate_both_sides":
                    passed, details, certificates, error_msg = self._verify_differentiate_both_sides(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "differentiate":
                    passed, details, certificates, error_msg = self._verify_differentiate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule in ("chain_rule", "product_rule", "quotient_rule"):
                    passed, details, certificates, error_msg = self._verify_composite_derivative_rule(
                        rule, out_nodes[0], edge.parameters
                    )
                elif rule == "implicit_differentiate":
                    passed, details, certificates, error_msg = self._verify_implicit_differentiate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "integrate":
                    passed, details, certificates, error_msg = self._verify_integrate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "nested_integrate":
                    passed, details, certificates, error_msg = self._verify_nested_integrate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "integration_by_substitution":
                    passed, details, certificates, error_msg = self._verify_integration_by_substitution(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "integration_by_parts":
                    passed, details, certificates, error_msg = self._verify_integration_by_parts(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "partial_fractions_integrate":
                    passed, details, certificates, error_msg = self._verify_partial_fractions_integrate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "trigonometric_integrate":
                    passed, details, certificates, error_msg = self._verify_trigonometric_integrate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "substitute":
                    passed, details, certificates, error_msg = self._verify_substitute(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "simplify":
                    passed, details, certificates, error_msg = self._verify_simplify(
                        in_nodes[0], out_nodes[0]
                    )
                elif rule == "improper_integral":
                    passed, details, certificates, error_msg = self._verify_improper_integral(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "fundamental_theorem_calculus":
                    passed, details, certificates, error_msg = self._verify_fundamental_theorem(
                        in_nodes, out_nodes, edge.parameters
                    )
                elif rule == "limit":
                    passed, details, certificates, error_msg = self._verify_limit(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "continuity":
                    passed, details, certificates, error_msg = self._verify_continuity(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )

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

            if details.get("_status_override"):
                status = VerificationStatus(details.pop("_status_override"))
            else:
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

    def _verify_ode_rule(
        self,
        rule: str,
        in_nodes: List[Any],
        out_nodes: List[Any],
        params: Dict[str, Any],
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str], VerificationStatus]:
        """Route all reusable ODE capabilities through one semantic engine."""
        variable = str(params.get("variable", "t"))
        coordinate_names = params.get("coordinates")
        default_function = (
            coordinate_names[0]
            if isinstance(coordinate_names, list) and coordinate_names
            else "y"
        )
        function = str(
            params.get("function", params.get("dependent_variable", default_function))
        )
        engine = ODEEngine(variable=variable, function=function)
        equation = in_nodes[0].expression.raw_str
        candidate = out_nodes[0].expression.raw_str
        try:
            if rule in {"solve_harmonic_oscillator", "verify_ode_solution"}:
                result = engine.verify_solution(equation, candidate, params)
            elif rule == "solve_separable_ode":
                result = engine.verify_separable(equation, candidate, params)
            elif rule == "solve_linear_first_order_ode":
                result = engine.verify_linear_first_order(equation, candidate, params)
            elif rule == "solve_bernoulli_ode":
                result = engine.verify_bernoulli(equation, candidate, params)
            elif rule == "solve_exact_ode":
                result = engine.verify_exact(equation, candidate, params)
            elif rule == "solve_constant_coefficient_ode":
                result = engine.verify_constant_coefficient(equation, candidate, params)
            elif rule == "verify_ode_ivp":
                result = engine.verify_ivp(equation, candidate, params)
            elif rule == "verify_ode_bvp":
                result = engine.verify_bvp(equation, candidate, params)
            elif rule == "verify_ode_system":
                result = engine.verify_system(equation, candidate, params)
            elif rule == "ode_phase_space":
                result = engine.phase_space(equation, candidate, params)
            else:
                return (
                    False,
                    {"rule": rule},
                    [],
                    "Unsupported ODE rule.",
                    VerificationStatus.NOT_APPLICABLE,
                )
        except Exception as exc:
            return (
                False,
                {"rule": rule},
                [],
                f"ODE engine error: {type(exc).__name__}: {exc}",
                VerificationStatus.FAILED,
            )
        try:
            status = VerificationStatus(result.status)
        except ValueError:
            status = VerificationStatus.UNVERIFIED
        details = dict(result.details)
        details["rule"] = rule
        return result.passed, details, result.steps, result.error, status

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
        sol_local: Dict[str, Any] = {
            "t": t,
            **param_syms,
            **aux_syms,
        }

        from automate.ir.safe_parser import SafeParser, SafeParseError
        sol_parser = SafeParser(extra_symbols={
            k: v for k, v in {**param_syms, **aux_syms, "t": t}.items()
            if isinstance(v, sp.Basic)
        })

        actual_sol_str = sol_str.strip()
        if "=" in actual_sol_str:
            lhs_s, rhs_s = actual_sol_str.split("=", 1)
            lhs_s = lhs_s.strip()
            if lhs_s in (f"{q0}(t)", q0, f"{q0}(t, )"):
                actual_sol_str = rhs_s.strip()
            else:
                actual_sol_str = rhs_s.strip()

        try:
            sol_expr = sol_parser.parse(actual_sol_str, extra_locals=sol_local)
        except SafeParseError as e:
            return False, {"rule": "solve_ode", "ode": ode_str, "solution": sol_str}, [], \
                f"SafeParser rejected candidate solution: {e}"
        except Exception as e:
            return False, {"rule": "solve_ode", "ode": ode_str, "solution": sol_str}, [], \
                f"Candidate solution parse error: {type(e).__name__}: {str(e)}"

        # Parse the ODE expression via SafeParser
        ode_parser = SafeParser(extra_symbols={
            k: v for k, v in {**param_syms, **aux_syms, "t": t}.items()
            if isinstance(v, sp.Basic)
        })
        try:
            if "=" in ode_str:
                parts = ode_str.split("=", 1)
                ode_lhs = ode_parser.parse(parts[0].strip(), extra_locals=ode_syms)
                ode_rhs = ode_parser.parse(parts[1].strip(), extra_locals=ode_syms)
                ode_expr = ode_lhs - ode_rhs
            else:
                ode_expr = ode_parser.parse(ode_str, extra_locals=ode_syms)
        except SafeParseError as e:
            return False, {"rule": "solve_ode", "ode": ode_str, "solution": sol_str}, [], \
                f"SafeParser rejected ODE expression: {e}"
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

        # Substitute parameter aliases (e.g. omega = sqrt(k/m)) before zero-test.
        # Uses SafeParser — no bare sympify.
        alias_subs: Dict[sp.Expr, sp.Expr] = {}
        alias_local: Dict[str, Any] = {**param_syms, **aux_syms, "t": t}
        alias_parser = SafeParser()
        for p_key, p_val in params.items():
            if p_key in ("coordinates", "parameters", "numerical_parameters",
                         "initial_conditions", "initial_velocities", "t_max"):
                continue
            if isinstance(p_val, str) and p_val.strip():
                try:
                    alias_sym = aux_syms.get(p_key) or param_syms.get(p_key) or sp.Symbol(p_key, real=True)
                    alias_expr_parsed = alias_parser.parse(p_val.strip(), extra_locals=alias_local)
                    if isinstance(alias_sym, sp.Symbol):
                        alias_subs[alias_sym] = alias_expr_parsed
                except (SafeParseError, Exception):
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
    # Rule: divide_both_sides
    # Verifies that out_expr == in_expr / divisor.
    # ------------------------------------------------------------------
    @staticmethod
    def _prove_symbolic_nonzero(
        divisor: sp.Expr,
        graph: DerivationGraph,
        side_condition_ids: List[str],
    ) -> tuple[bool, Optional[str]]:
        """Prove a divisor is non-zero using the central assumption engine.

        Backend rules do not contain their own implication heuristics. The
        entailment layer evaluates the complete active assumption context and
        returns proof only when its reasoning engine is affirmative.
        """
        from automate.ir.assumption_logic import AssumptionEntailment
        return AssumptionEntailment(graph).entails_nonzero(
            divisor,
            side_condition_ids,
        )

    def _verify_divide_both_sides(
        self,
        in_node: Any,
        out_node: Any,
        params: Dict[str, Any],
        graph: Optional[DerivationGraph] = None,
        side_condition_ids: Optional[List[str]] = None,
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError

        divisor_str = params.get("divisor", "")
        if not divisor_str:
            return False, {"rule": "divide_both_sides"}, [],                 "UNSUPPORTED: edge.parameters['divisor'] required for divide_both_sides rule."

        parser = SafeParser()
        try:
            in_expr = parser.parse(in_node.expression.raw_str)
            out_expr = parser.parse(out_node.expression.raw_str)
            div_expr = parser.parse(str(divisor_str))
        except SafeParseError as e:
            return False, {"rule": "divide_both_sides"}, [], f"SafeParser error: {e}"

        if div_expr == 0:
            return False, {"rule": "divide_both_sides", "divisor": str(div_expr)}, [],                 "Division by zero: divisor is zero."

        nonzero_proven = False
        nonzero_source: Optional[str] = None

        if div_expr.is_number:
            nonzero_proven = bool(div_expr != 0)
            nonzero_source = "numeric divisor"
        elif graph is not None:
            nonzero_proven, nonzero_source = self._prove_symbolic_nonzero(
                div_expr, graph, side_condition_ids or []
            )

        if not nonzero_proven:
            return (
                False,
                {
                    "rule": "divide_both_sides",
                    "divisor": str(div_expr),
                    "nonzero_proven": False,
                    "side_conditions_considered": side_condition_ids or [],
                },
                [],
                f"UNSUPPORTED: symbolic divisor '{div_expr}' is not proven non-zero.",
            )

        expected = sp.simplify(in_expr / div_expr)
        diff = sp.simplify(out_expr - expected)
        passed = (diff == 0)
        details = {
            "in_expr": str(in_expr),
            "divisor": str(div_expr),
            "nonzero_proven": nonzero_proven,
            "nonzero_source": nonzero_source,
            "expected_out": str(expected),
            "actual_out": str(out_expr),
            "diff": str(diff),
        }
        steps = [
            {"step": 1, "operation": "parse_divisor", "expr": str(div_expr)},
            {"step": 2, "operation": "prove_divisor_nonzero", "source": nonzero_source},
            {"step": 3, "operation": "in_expr / divisor", "expr": str(expected)},
            {"step": 4, "operation": "simplify(actual - expected)", "expr": str(diff)},
        ]
        err = None if passed else f"divide_both_sides mismatch: expected {expected}, got {out_expr}"
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: differentiate
    # General scalar symbolic differentiation with arbitrary positive
    # integer derivative order.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_differentiate(
        cls, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip() or not variable_name.strip().isidentifier():
            return False, {"rule": "differentiate"}, [], "Malformed derivative variable: parameters['variable'] must be a valid identifier."
        order = params.get("order", 1)
        if isinstance(order, bool) or not isinstance(order, int) or order < 1:
            return False, {"rule": "differentiate", "order": order}, [], "Malformed derivative order: parameters['order'] must be a positive integer."
        raw_assumptions = params.get("assumptions") or {}
        if not isinstance(raw_assumptions, dict):
            return False, {"rule": "differentiate"}, [], "Malformed assumptions: parameters['assumptions'] must be an object."
        allowed = {"real", "positive", "negative", "nonzero", "integer"}
        symbols: Dict[str, sp.Symbol] = {}
        try:
            for name, assumption in raw_assumptions.items():
                if not isinstance(name, str) or not name.isidentifier():
                    raise ValueError("Assumption symbol names must be valid identifiers.")
                items = assumption if isinstance(assumption, list) else [assumption]
                props = {}
                for item in items:
                    if item not in allowed:
                        raise ValueError(f"Unsupported symbolic assumption '{item}'.")
                    props[item] = True
                symbols[name] = sp.Symbol(name, **props)
        except (TypeError, ValueError) as exc:
            return False, {"rule": "differentiate", "order": order}, [], f"Malformed assumptions: {exc}"
        variable = symbols.get(variable_name, sp.Symbol(variable_name, real=True))
        parser = SafeParser(extra_symbols=symbols | {variable_name: variable})
        try:
            in_expr = parser.parse(in_node.expression.raw_str)
            out_expr = parser.parse(out_node.expression.raw_str)
        except SafeParseError as exc:
            return False, {"rule": "differentiate", "order": order}, [], f"SafeParser rejected derivative expression: {exc}"
        try:
            expected = sp.diff(in_expr, variable, order)
        except (NotImplementedError, ValueError, TypeError, ZeroDivisionError) as exc:
            return False, {"rule": "differentiate", "order": order}, [], f"UNVERIFIED: differentiation could not be established: {type(exc).__name__}: {exc}"
        try:
            residual = sp.simplify(out_expr - expected)
        except (NotImplementedError, ValueError, TypeError, ZeroDivisionError) as exc:
            return False, {
                "rule": "differentiate", "order": order,
                "expected_derivative": str(expected), "actual_derivative": str(out_expr),
                "_status_override": VerificationStatus.UNVERIFIED.value,
            }, [], f"UNVERIFIED: derivative comparison remained unresolved: {type(exc).__name__}: {exc}"
        equivalence = residual.equals(0) if hasattr(residual, "equals") else (residual == 0)
        if residual == 0 or equivalence is True:
            passed, status_override, error = True, None, None
        elif equivalence is False:
            passed, status_override = False, None
            error = f"Derivative mismatch: expected {expected}, got {out_expr}."
        else:
            passed, status_override = False, VerificationStatus.UNVERIFIED.value
            error = "UNVERIFIED: symbolic derivative comparison could not establish equality."
        domain_details: Dict[str, str] = {}
        try:
            domain_details["input_real_domain"] = str(sp.calculus.util.continuous_domain(in_expr, variable, sp.S.Reals))
        except (NotImplementedError, ValueError, TypeError):
            domain_details["input_real_domain"] = "UNDETERMINED"
        try:
            domain_details["derivative_real_domain"] = str(sp.calculus.util.continuous_domain(expected, variable, sp.S.Reals))
        except (NotImplementedError, ValueError, TypeError):
            domain_details["derivative_real_domain"] = "UNDETERMINED"
        details = {
            "rule": "differentiate", "variable": str(variable), "order": order,
            "input_expression": str(in_expr), "expected_derivative": str(expected),
            "actual_derivative": str(out_expr), "residual": str(residual),
            "domain_analysis": domain_details,
        }
        if status_override:
            details["_status_override"] = status_override
        steps = [
            {"step": 1, "operation": "differentiate", "variable": str(variable), "order": order,
             "input": str(in_expr), "result": str(expected)},
            {"step": 2, "operation": "simplify(actual - expected)", "residual": str(residual)},
        ]
        return passed, details, steps, error

    # ------------------------------------------------------------------
    # Rules: explicit composite differentiation
    # These rules verify the named chain/product/quotient construction itself,
    # rather than merely accepting an equivalent final derivative.
    # ------------------------------------------------------------------
    @classmethod
    def _parse_composite(cls, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        parser = SafeParser()
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip() or not variable_name.strip().isidentifier():
            raise ValueError("parameters['variable'] must be a valid identifier.")
        variable = parser.make_symbol(variable_name.strip())
        kind = params.get("_rule_kind")
        if kind == "chain_rule":
            outer = parser.parse(str(params["outer"]))
            inner = parser.parse(str(params["inner"]))
            expression = outer.subs(parser.make_symbol(str(params.get("inner_variable", "u"))), inner)
            expected = sp.diff(outer, parser.make_symbol(str(params.get("inner_variable", "u")))).subs(parser.make_symbol(str(params.get("inner_variable", "u"))), inner) * sp.diff(inner, variable)
            return variable, expression, expected, {"outer": outer, "inner": inner}
        if kind == "product_rule":
            factors = params.get("factors")
            if not isinstance(factors, list) or len(factors) < 2:
                raise ValueError("parameters['factors'] must contain at least two expressions.")
            factor_exprs = [parser.parse(str(v)) for v in factors]
            expression = sp.prod(factor_exprs)
            expected = sum(
                sp.diff(factor_exprs[i], variable) * sp.prod(
                    factor_exprs[j] for j in range(len(factor_exprs)) if j != i
                ) for i in range(len(factor_exprs))
            )
            return variable, expression, expected, {"factors": factor_exprs}
        if kind == "quotient_rule":
            numerator = parser.parse(str(params["numerator"]))
            denominator = parser.parse(str(params["denominator"]))
            if denominator == 0:
                raise ValueError("parameters['denominator'] must not be identically zero.")
            expression = numerator / denominator
            expected = (sp.diff(numerator, variable) * denominator -
                        numerator * sp.diff(denominator, variable)) / denominator**2
            return variable, expression, expected, {"numerator": numerator, "denominator": denominator}
        raise ValueError("Unsupported composite derivative rule.")

    @classmethod
    def _verify_composite_derivative_rule(
        cls, rule: str, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        params = dict(params or {})
        params["_rule_kind"] = rule
        try:
            variable, expression, expected, components = cls._parse_composite(params)
            actual = SafeParser().parse(out_node.expression.raw_str)
        except (SafeParseError, KeyError, TypeError, ValueError) as exc:
            return False, {"rule": rule}, [], f"Malformed {rule} parameters/expression: {exc}"
        try:
            residual = sp.simplify(actual - expected)
        except Exception as exc:
            return (
                False, {"rule": rule, "expected_derivative": str(expected)}, [],
                f"UNVERIFIED: {rule} comparison remained unresolved: {type(exc).__name__}: {exc}"
            )
        equivalence = residual.equals(0) if hasattr(residual, "equals") else (residual == 0)
        if residual == 0 or equivalence is True:
            passed, override, error = True, None, None
        elif equivalence is False:
            passed, override, error = False, None, f"{rule} mismatch: expected {expected}, got {actual}."
        else:
            passed, override, error = False, VerificationStatus.UNVERIFIED.value, f"UNVERIFIED: {rule} comparison could not establish equality."
        details = {
            "rule": rule, "variable": str(variable), "expression": str(expression),
            "expected_derivative": str(expected), "actual_derivative": str(actual),
            "residual": str(residual),
            "components": {k: [str(x) for x in v] if isinstance(v, list) else str(v) for k, v in components.items()},
        }
        if override:
            details["_status_override"] = override
        steps = [
            {"step": 1, "operation": rule, "expression": str(expression), "result": str(expected)},
            {"step": 2, "operation": "simplify(actual - expected)", "residual": str(residual)},
        ]
        return passed, details, steps, error

    # ------------------------------------------------------------------
    # Rule: implicit_differentiate
    # Verifies dy/dx from an explicit implicit relation F(x,y)=0.
    # The denominator F_y must be structurally nonzero; if it cannot be
    # established, verification fails closed as UNVERIFIED.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_implicit_differentiate(
        cls, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        x_name = params.get("independent_variable", params.get("variable", ""))
        y_name = params.get("dependent_variable", "")
        if (not isinstance(x_name, str) or not x_name.strip().isidentifier() or
                not isinstance(y_name, str) or not y_name.strip().isidentifier() or
                x_name.strip() == y_name.strip()):
            return False, {"rule": "implicit_differentiate"}, [], "Malformed implicit differentiation variables."
        parser = SafeParser()
        try:
            x = parser.make_symbol(x_name.strip())
            y = parser.make_symbol(y_name.strip())
            relation = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
        except SafeParseError as exc:
            return False, {"rule": "implicit_differentiate"}, [], f"SafeParser rejected implicit differentiation input: {exc}"
        try:
            fy = sp.diff(relation, y)
            fx = sp.diff(relation, x)
            expected = -fx / fy
            if fy == 0:
                return (
                    False, {"rule": "implicit_differentiate", "F_x": str(fx), "F_y": str(fy),
                           "_status_override": VerificationStatus.UNVERIFIED.value}, [],
                    "UNVERIFIED: implicit derivative denominator F_y is identically zero."
                )
            residual = sp.simplify(actual - expected)
        except Exception as exc:
            return (
                False, {"rule": "implicit_differentiate"}, [],
                f"UNVERIFIED: implicit differentiation could not be established: {type(exc).__name__}: {exc}"
            )
        equivalence = residual.equals(0) if hasattr(residual, "equals") else (residual == 0)
        if residual == 0 or equivalence is True:
            passed, override, error = True, None, None
        elif equivalence is False:
            passed, override, error = False, None, f"Implicit derivative mismatch: expected {expected}, got {actual}."
        else:
            passed, override, error = False, VerificationStatus.UNVERIFIED.value, "UNVERIFIED: implicit derivative comparison could not establish equality."
        details = {
            "rule": "implicit_differentiate", "independent_variable": str(x),
            "dependent_variable": str(y), "relation": str(relation),
            "F_x": str(fx), "F_y": str(fy), "expected_derivative": str(expected),
            "actual_derivative": str(actual), "residual": str(residual),
            "local_condition": f"{y_name}'s partial derivative F_y != 0",
        }
        if override:
            details["_status_override"] = override
        steps = [
            {"step": 1, "operation": "compute_partial_F_x", "result": str(fx)},
            {"step": 2, "operation": "compute_partial_F_y", "result": str(fy)},
            {"step": 3, "operation": "-F_x/F_y", "result": str(expected)},
            {"step": 4, "operation": "simplify(actual - expected)", "residual": str(residual)},
        ]
        return passed, details, steps, error

    # ------------------------------------------------------------------
    # Rule: differentiate_both_sides
    # Verifies that out_expr == d(in_expr)/d(wrt).
    # ------------------------------------------------------------------
    def _verify_differentiate_both_sides(
        self, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        wrt_str = params.get("wrt", "")
        if not wrt_str:
            return False, {"rule": "differentiate_both_sides"}, [], \
                "UNSUPPORTED: edge.parameters['wrt'] required for differentiate_both_sides rule."
        parser = SafeParser()
        try:
            in_expr  = parser.parse(in_node.expression.raw_str)
            out_expr = parser.parse(out_node.expression.raw_str)
            wrt_sym  = parser.make_symbol(str(wrt_str).strip())
        except SafeParseError as e:
            return False, {"rule": "differentiate_both_sides"}, [], f"SafeParser error: {e}"

        try:
            expected = sp.diff(in_expr, wrt_sym)
        except Exception as e:
            return False, {"rule": "differentiate_both_sides"}, [], \
                f"Differentiation error: {type(e).__name__}: {e}"

        diff = sp.simplify(out_expr - expected)
        passed = (diff == 0)
        details = {
            "in_expr": str(in_expr),
            "wrt": str(wrt_sym),
            "expected_derivative": str(expected),
            "actual_out": str(out_expr),
            "diff": str(diff),
        }
        steps = [
            {"step": 1, "operation": f"d(in_expr)/d({wrt_sym})", "expr": str(expected)},
            {"step": 2, "operation": "simplify(actual - expected)", "expr": str(diff)},
        ]
        err = None if passed else f"differentiate_both_sides mismatch: expected {expected}, got {out_expr}"
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: integrate
    # Verifies definite and indefinite symbolic integration. For indefinite
    # integration, the candidate is checked by differentiating it the
    # requested number of times, so arbitrary integration order does not
    # require a hard-coded antiderivative constant convention.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_integrate(
        cls, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip() or not variable_name.strip().isidentifier():
            return False, {"rule": "integrate"}, [], "Malformed integration variable: parameters['variable'] must be a valid identifier."
        order = params.get("order", 1)
        if isinstance(order, bool) or not isinstance(order, int) or order < 1:
            return False, {"rule": "integrate", "order": order}, [], "Malformed integration order: parameters['order'] must be a positive integer."
        parser = SafeParser()
        try:
            variable = parser.make_symbol(variable_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
        except SafeParseError as exc:
            return False, {"rule": "integrate", "order": order}, [], f"SafeParser rejected integration expression: {exc}"

        lower_raw = params.get("lower")
        upper_raw = params.get("upper")
        if (lower_raw is None) != (upper_raw is None):
            return False, {"rule": "integrate"}, [], "Malformed definite integration bounds: both 'lower' and 'upper' are required together."
        definite = lower_raw is not None
        try:
            if definite:
                lower = parser.parse(str(lower_raw))
                upper = parser.parse(str(upper_raw))
                if order != 1:
                    return False, {"rule": "integrate", "order": order}, [], "Unsupported: repeated definite integration is not yet represented; use order=1."
                expected = sp.integrate(integrand, (variable, lower, upper))
                if isinstance(expected, sp.Integral) or expected.has(sp.Integral):
                    return False, {
                        "rule": "integrate", "mode": "definite", "order": order,
                        "integrand": str(integrand), "lower": str(lower), "upper": str(upper),
                        "_status_override": VerificationStatus.UNVERIFIED.value,
                    }, [], "UNVERIFIED: definite integral remained unevaluated."
                residual = sp.simplify(actual - expected)
            else:
                lower = upper = None
                expected = sp.integrate(integrand, variable)
                if isinstance(expected, sp.Integral) or expected.has(sp.Integral):
                    return False, {
                        "rule": "integrate", "mode": "indefinite", "order": order,
                        "integrand": str(integrand),
                        "_status_override": VerificationStatus.UNVERIFIED.value,
                    }, [], "UNVERIFIED: indefinite integral remained unevaluated."
                # Verify the candidate directly rather than requiring the
                # backend's particular choice of integration constant/polynomial.
                actual_check = actual
                for _ in range(order):
                    actual_check = sp.diff(actual_check, variable)
                residual = sp.simplify(actual_check - integrand)
            equivalence = residual.equals(0) if hasattr(residual, "equals") else (residual == 0)
        except (NotImplementedError, ValueError, TypeError, ZeroDivisionError) as exc:
            return (
                False, {"rule": "integrate", "order": order}, [],
                f"UNVERIFIED: integration/comparison could not be established: {type(exc).__name__}: {exc}"
            )
        if residual == 0 or equivalence is True:
            passed, override, error = True, None, None
        elif equivalence is False:
            passed, override = False, None
            error = f"Integral mismatch: expected {expected}, got {actual}."
        else:
            passed, override = False, VerificationStatus.UNVERIFIED.value
            error = "UNVERIFIED: symbolic integral comparison could not establish equality."
        details = {
            "rule": "integrate", "mode": "definite" if definite else "indefinite",
            "variable": str(variable), "order": order, "integrand": str(integrand),
            "expected_result": str(expected), "actual_result": str(actual),
            "residual": str(residual),
        }
        if definite:
            details.update({"lower": str(lower), "upper": str(upper)})
        if override:
            details["_status_override"] = override
        steps = [
            {"step": 1, "operation": "integrate" if definite else f"integrate_order_{order}", "result": str(expected)},
            {"step": 2, "operation": "differentiate_candidate" if not definite else "simplify(actual - expected)", "residual": str(residual)},
        ]
        return passed, details, steps, error

    @classmethod
    def _verify_improper_integral(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        """Verify convergence and value of a one-dimensional improper integral.

        Supported representations are infinite bounds and endpoint/interior
        singularities. The verifier constructs a truncated proper integral and
        requires its limit to establish a finite result. It never treats an
        unevaluated or indeterminate limit as convergence.
        """
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip().isidentifier():
            return False, {"rule": "improper_integral"}, [], "Malformed integration variable."
        parser = SafeParser()
        try:
            variable = parser.make_symbol(variable_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
        except SafeParseError as exc:
            return False, {"rule": "improper_integral"}, [], f"SafeParser rejected improper integral: {exc}"

        lower_raw, upper_raw = params.get("lower"), params.get("upper")
        singular_raw = params.get("singular_point")
        if lower_raw is None or upper_raw is None:
            return False, {"rule": "improper_integral"}, [], "Improper integral requires explicit lower and upper bounds."
        if singular_raw is not None and (str(lower_raw) == str(singular_raw) or str(upper_raw) == str(singular_raw)):
            return False, {"rule": "improper_integral"}, [], "Use endpoint='lower' or endpoint='upper' for endpoint singularities."
        try:
            lower = parser.parse(str(lower_raw))
            upper = parser.parse(str(upper_raw))
            if params.get("endpoint") in ("lower", "upper"):
                endpoint = params["endpoint"]
                singular = lower if endpoint == "lower" else upper
                direction = "right" if endpoint == "lower" else "left"
                eps = sp.symbols("epsilon", positive=True)
                cutoff = singular + eps if direction == "right" else singular - eps
                truncated = (\n                    sp.integrate(integrand, (variable, cutoff, upper))\n                    if endpoint == "lower"\n                    else sp.integrate(integrand, (variable, lower, cutoff))\n                )
                if isinstance(truncated, sp.Integral) or truncated.has(sp.Integral):
                    return False, {"rule": "improper_integral", "mode": "endpoint", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: truncated integral remained unevaluated."
                limit_value = sp.limit(truncated, eps, 0, dir="+")
            elif singular_raw is not None:
                singular = parser.parse(str(singular_raw))
                eps = sp.symbols("epsilon", positive=True)
                left = sp.integrate(integrand, (variable, lower, singular - eps))
                right = sp.integrate(integrand, (variable, singular + eps, upper))
                if left.has(sp.Integral) or right.has(sp.Integral):
                    return False, {"rule": "improper_integral", "mode": "interior", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: truncated interior integrals remained unevaluated."
                left_limit, right_limit = sp.limit(left, eps, 0, dir="+"), sp.limit(right, eps, 0, dir="+")
                if left_limit in (sp.oo, -sp.oo, sp.zoo) or right_limit in (sp.oo, -sp.oo, sp.zoo):
                    return False, {"rule": "improper_integral", "mode": "interior", "converges": False, "left_limit": str(left_limit), "right_limit": str(right_limit)}, [{"step": 1, "operation": "endpoint_limits", "left": str(left_limit), "right": str(right_limit)}], "Verified divergence: at least one one-sided integral diverges."
                if left_limit.has(sp.Limit) or right_limit.has(sp.Limit):
                    return False, {"rule": "improper_integral", "mode": "interior", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: convergence could not be established."
                limit_value = sp.simplify(left_limit + right_limit)
            else:
                # Infinite bounds are handled by the same epsilon-limit construction.
                # For two-sided infinite intervals, convergence requires both tails
                # to converge separately. This intentionally avoids silently using
                # a symmetric principal value as ordinary convergence.
                eps = sp.symbols("epsilon", positive=True)
                if upper in (sp.oo, -sp.oo) and lower in (sp.oo, -sp.oo):
                    if lower == sp.oo or upper == -sp.oo:
                        return False, {"rule": "improper_integral"}, [], "Malformed infinite bounds: lower and upper must define an ordered interval."
                    left_cut = lower + eps if lower == -sp.oo else lower - eps
                    right_cut = upper - eps if upper == sp.oo else upper + eps
                    left_piece = sp.integrate(integrand, (variable, lower, 0))
                    right_piece = sp.integrate(integrand, (variable, 0, upper))
                    if left_piece.has(sp.Integral) or right_piece.has(sp.Integral):
                        return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: two-sided tail integral remained unevaluated."
                    left_limit = sp.limit(sp.integrate(integrand, (variable, lower + eps, 0)), eps, 0, dir="+")
                    right_limit = sp.limit(sp.integrate(integrand, (variable, 0, upper - eps)), eps, 0, dir="+")
                    if left_limit in (sp.oo, -sp.oo, sp.zoo) or right_limit in (sp.oo, -sp.oo, sp.zoo):
                        return False, {"rule": "improper_integral", "converges": False, "left_limit": str(left_limit), "right_limit": str(right_limit)}, [{"step": 1, "operation": "two_sided_tail_limits", "left": str(left_limit), "right": str(right_limit)}], "Verified divergence: at least one infinite tail diverges."
                    if left_limit.has(sp.Limit) or right_limit.has(sp.Limit) or left_limit is sp.nan or right_limit is sp.nan:
                        return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: two-sided convergence could not be established."
                    limit_value = sp.simplify(left_limit + right_limit)
                elif upper in (sp.oo, -sp.oo):
                    truncated = sp.integrate(integrand, (variable, lower, upper - eps if upper == sp.oo else upper + eps))
                    if truncated.has(sp.Integral):
                        return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: truncated integral remained unevaluated."
                    limit_value = sp.limit(truncated, eps, 0, dir="+")
                elif lower in (sp.oo, -sp.oo):
                    truncated = sp.integrate(integrand, (variable, lower + eps if lower == sp.oo else lower - eps, upper))
                    if truncated.has(sp.Integral):
                        return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: truncated integral remained unevaluated."
                    limit_value = sp.limit(truncated, eps, 0, dir="+")
                else:
                    return False, {"rule": "improper_integral"}, [], "Finite bounds require singular_point or endpoint specification."
            if limit_value in (sp.oo, -sp.oo, sp.zoo):
                return False, {"rule": "improper_integral", "converges": False, "limit": str(limit_value)}, [{"step": 1, "operation": "convergence_limit", "result": str(limit_value)}], "Verified divergence of improper integral."
            if limit_value.has(sp.Limit) or limit_value is sp.nan:
                return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: convergence limit is indeterminate or unevaluated."
            residual = sp.simplify(actual - limit_value)
            equivalent = residual.equals(0) if hasattr(residual, "equals") else residual == 0
            if residual == 0 or equivalent is True:
                return True, {"rule": "improper_integral", "converges": True, "expected_result": str(limit_value), "actual_result": str(actual), "residual": str(residual)}, [{"step": 1, "operation": "convergence_limit", "result": str(limit_value)}, {"step": 2, "operation": "compare_claimed_value", "residual": str(residual)}], None
            if equivalent is False:
                return False, {"rule": "improper_integral", "converges": True, "expected_result": str(limit_value), "actual_result": str(actual), "residual": str(residual)}, [], "Improper integral converges, but claimed value is incorrect."
            return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: convergent value comparison could not establish equality."
        except Exception as exc:
            return False, {"rule": "improper_integral", "_status_override": VerificationStatus.UNVERIFIED.value}, [], f"UNVERIFIED: improper-integral analysis failed: {type(exc).__name__}: {exc}"

    # ------------------------------------------------------------------
    # Rule: integration_by_substitution
    # Explicitly represents u = g(x) and the transformed integrand in u.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_integration_by_substitution(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        u_name = params.get("substitution_variable")
        g_raw = params.get("substitution_expression")
        transformed_raw = params.get("transformed_integrand")
        if (not isinstance(variable_name, str) or not variable_name.strip().isidentifier()
                or not isinstance(u_name, str) or not u_name.strip().isidentifier()
                or not isinstance(g_raw, str) or not g_raw.strip()
                or not isinstance(transformed_raw, str) or not transformed_raw.strip()):
            return False, {"rule": "integration_by_substitution"}, [], (
                "Malformed substitution: variable, substitution_variable, substitution_expression, "
                "and transformed_integrand are required."
            )
        if variable_name.strip() == u_name.strip():
            return False, {"rule": "integration_by_substitution"}, [], (
                "Malformed substitution: integration and substitution variables must differ."
            )
        parser = SafeParser()
        try:
            x = parser.make_symbol(variable_name.strip())
            u = parser.make_symbol(u_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
            g = parser.parse(g_raw)
            transformed = parser.parse(transformed_raw)
        except SafeParseError as exc:
            return False, {"rule": "integration_by_substitution"}, [], f"SafeParser rejected substitution expression: {exc}"
        try:
            if not g.has(x):
                return False, {"rule": "integration_by_substitution"}, [], (
                    "Malformed substitution: substitution_expression must depend on the integration variable."
                )
            du_dx = sp.diff(g, x)
            if du_dx == 0 or du_dx.equals(0) is True:
                return False, {"rule": "integration_by_substitution", "du_dx": str(du_dx)}, [], (
                    "Invalid substitution: du/dx is identically zero."
                )
            transformed_back = sp.simplify(transformed.subs(u, g) * du_dx - integrand)
            transform_equivalence = transformed_back.equals(0) if hasattr(transformed_back, "equals") else transformed_back == 0
            candidate_residual = sp.simplify(sp.diff(actual, x) - integrand)
            candidate_equivalence = candidate_residual.equals(0) if hasattr(candidate_residual, "equals") else candidate_residual == 0
        except Exception as exc:
            return False, {"rule": "integration_by_substitution"}, [], (
                f"UNVERIFIED: substitution verification could not be established: {type(exc).__name__}: {exc}"
            )
        details = {
            "rule": "integration_by_substitution", "variable": str(x),
            "substitution_variable": str(u), "substitution_expression": str(g),
            "du_dx": str(du_dx), "transformed_integrand": str(transformed),
            "transformed_back_residual": str(transformed_back),
            "candidate_result": str(actual), "candidate_residual": str(candidate_residual),
            "domain_note": "The represented differential identity and antiderivative are verified; global one-to-one/invertibility is not inferred.",
        }
        if transform_equivalence is False or candidate_equivalence is False:
            return False, details, [], "FAIL: substitution transformation or antiderivative candidate is incorrect."
        if transform_equivalence is not True or candidate_equivalence is not True:
            details["_status_override"] = VerificationStatus.UNVERIFIED.value
            return False, details, [], "UNVERIFIED: symbolic substitution equality could not be established."
        return True, details, [
            {"step": 1, "operation": f"u = {g}", "result": str(u)},
            {"step": 2, "operation": "compute_du_dx", "result": str(du_dx)},
            {"step": 3, "operation": "substitute_u_and_restore_dx", "residual": str(transformed_back)},
            {"step": 4, "operation": "differentiate_candidate", "residual": str(candidate_residual)},
        ], None

    # ------------------------------------------------------------------
    # Rule: integration_by_parts
    # Represents u, dv, and v explicitly and verifies the parts identity.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_integration_by_parts(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        u_raw, dv_raw, v_raw = params.get("u"), params.get("dv"), params.get("v")
        if (not isinstance(variable_name, str) or not variable_name.strip().isidentifier()
                or not all(isinstance(v, str) and v.strip() for v in (u_raw, dv_raw, v_raw))):
            return False, {"rule": "integration_by_parts"}, [], (
                "Malformed integration by parts: variable, u, dv, and v are required strings."
            )
        parser = SafeParser()
        try:
            x = parser.make_symbol(variable_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
            u = parser.parse(u_raw); dv = parser.parse(dv_raw); v = parser.parse(v_raw)
        except SafeParseError as exc:
            return False, {"rule": "integration_by_parts"}, [], f"SafeParser rejected integration-by-parts expression: {exc}"
        try:
            du = sp.diff(u, x)
            v_residual = sp.simplify(sp.diff(v, x) - dv)
            v_equivalence = v_residual.equals(0) if hasattr(v_residual, "equals") else v_residual == 0
            integrand_residual = sp.simplify(integrand - u * dv)
            integrand_equivalence = integrand_residual.equals(0) if hasattr(integrand_residual, "equals") else integrand_residual == 0
            remainder = sp.integrate(v * du, x)
            if isinstance(remainder, sp.Integral) or remainder.has(sp.Integral):
                return False, {"rule": "integration_by_parts", "u": str(u), "dv": str(dv), "v": str(v),
                               "du": str(du), "_status_override": VerificationStatus.UNVERIFIED.value}, [], (
                    "UNVERIFIED: the integration-by-parts remainder remained unevaluated."
                )
            parts_result = sp.simplify(u * v - remainder)
            candidate_residual = sp.simplify(sp.diff(actual - parts_result, x))
            candidate_equivalence = candidate_residual.equals(0) if hasattr(candidate_residual, "equals") else candidate_residual == 0
        except Exception as exc:
            return False, {"rule": "integration_by_parts"}, [], (
                f"UNVERIFIED: integration-by-parts verification could not be established: {type(exc).__name__}: {exc}"
            )
        details = {
            "rule": "integration_by_parts", "variable": str(x), "u": str(u), "dv": str(dv),
            "v": str(v), "du": str(du), "remainder_integral": str(remainder),
            "parts_result": str(parts_result), "v_residual": str(v_residual),
            "integrand_residual": str(integrand_residual), "candidate_result": str(actual),
            "candidate_residual": str(candidate_residual),
        }
        if v_equivalence is False or integrand_equivalence is False or candidate_equivalence is False:
            return False, details, [], "FAIL: the integration-by-parts identity or candidate result is incorrect."
        if v_equivalence is not True or integrand_equivalence is not True or candidate_equivalence is not True:
            details["_status_override"] = VerificationStatus.UNVERIFIED.value
            return False, details, [], "UNVERIFIED: symbolic integration-by-parts equality could not be established."
        return True, details, [
            {"step": 1, "operation": "du = differentiate(u)", "result": str(du)},
            {"step": 2, "operation": "verify(dv = differentiate(v))", "residual": str(v_residual)},
            {"step": 3, "operation": "integrate(v*du)", "result": str(remainder)},
            {"step": 4, "operation": "u*v - integral(v*du)", "result": str(parts_result)},
            {"step": 5, "operation": "differentiate_candidate_minus_parts_result", "residual": str(candidate_residual)},
        ], None

    # ------------------------------------------------------------------
    # Rule: partial_fractions_integrate
    # Represents a rational integrand and its proposed partial-fraction
    # decomposition, then verifies both decomposition and antiderivative.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_partial_fractions_integrate(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        decomposition_raw = params.get("decomposition")
        if (not isinstance(variable_name, str) or not variable_name.strip().isidentifier()
                or not isinstance(decomposition_raw, str) or not decomposition_raw.strip()):
            return False, {"rule": "partial_fractions_integrate"}, [], (
                "Malformed partial-fractions integration: variable and decomposition are required strings."
            )
        parser = SafeParser()
        try:
            x = parser.make_symbol(variable_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
            decomposition = parser.parse(decomposition_raw)
        except SafeParseError as exc:
            return False, {"rule": "partial_fractions_integrate"}, [], f"SafeParser rejected partial-fractions expression: {exc}"
        try:
            rational = sp.together(integrand)
            denominator = sp.factor(sp.denom(rational))
            if denominator == 0:
                return False, {"rule": "partial_fractions_integrate"}, [], "Invalid rational integrand: denominator is identically zero."
            if denominator == 1 or not denominator.has(x):
                return False, {"rule": "partial_fractions_integrate", "denominator": str(denominator)}, [], (
                    "Input is not a nontrivial rational function of the integration variable."
                )
            try:
                sp.Poly(sp.numer(rational), x); sp.Poly(sp.denom(rational), x)
            except (sp.PolynomialError, NotImplementedError):
                return False, {"rule": "partial_fractions_integrate", "denominator": str(denominator)}, [], (
                    "Input is not a rational function in the integration variable."
                )
            decomposition_residual = sp.cancel(sp.together(decomposition - integrand))
            decomposition_equivalence = decomposition_residual.equals(0) if hasattr(decomposition_residual, "equals") else decomposition_residual == 0
            canonical = sp.apart(integrand, x)
            canonical_residual = sp.cancel(sp.together(decomposition - canonical))
            canonical_equivalence = canonical_residual.equals(0) if hasattr(canonical_residual, "equals") else canonical_residual == 0
            candidate_residual = sp.simplify(sp.diff(actual, x) - integrand)
            candidate_equivalence = candidate_residual.equals(0) if hasattr(candidate_residual, "equals") else candidate_residual == 0
        except Exception as exc:
            return False, {"rule": "partial_fractions_integrate"}, [], (
                f"UNVERIFIED: partial-fractions verification could not be established: {type(exc).__name__}: {exc}"
            )
        details = {
            "rule": "partial_fractions_integrate", "variable": str(x), "integrand": str(integrand),
            "decomposition": str(decomposition), "canonical_decomposition": str(canonical),
            "decomposition_residual": str(decomposition_residual), "canonical_residual": str(canonical_residual),
            "candidate_result": str(actual), "candidate_residual": str(candidate_residual),
            "domain_restriction": f"{denominator} != 0",
        }
        if decomposition_equivalence is False or canonical_equivalence is False or candidate_equivalence is False:
            return False, details, [], "FAIL: partial-fraction decomposition or integrated candidate is incorrect."
        if decomposition_equivalence is not True or canonical_equivalence is not True or candidate_equivalence is not True:
            details["_status_override"] = VerificationStatus.UNVERIFIED.value
            return False, details, [], "UNVERIFIED: symbolic partial-fraction equality could not be established."
        return True, details, [
            {"step": 1, "operation": "compute_denominator_and_domain", "result": f"{denominator} != 0"},
            {"step": 2, "operation": "verify_partial_fraction_decomposition", "residual": str(decomposition_residual)},
            {"step": 3, "operation": "compare_with_canonical_apart", "residual": str(canonical_residual)},
            {"step": 4, "operation": "differentiate_candidate", "residual": str(candidate_residual)},
        ], None

    # ------------------------------------------------------------------
    # Rule: trigonometric_integrate
    # Dedicated tractable trig/hyperbolic integration path. Candidate and
    # backend primitive are both differentiated back to the integrand.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_trigonometric_integrate(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        from sympy.integrals.manualintegrate import manualintegrate
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip().isidentifier():
            return False, {"rule": "trigonometric_integrate"}, [], "Malformed trigonometric integration: variable must be a valid identifier."
        parser = SafeParser()
        try:
            x = parser.make_symbol(variable_name.strip())
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
        except SafeParseError as exc:
            return False, {"rule": "trigonometric_integrate"}, [], f"SafeParser rejected trigonometric integration expression: {exc}"
        try:
            if not any(integrand.has(fn) for fn in (sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot, sp.sinh, sp.cosh, sp.tanh, sp.sech, sp.csch, sp.coth)):
                return False, {"rule": "trigonometric_integrate"}, [], "Malformed trigonometric integration: integrand contains no supported trigonometric or hyperbolic function."
            expected = manualintegrate(integrand, x)
            if isinstance(expected, sp.Integral) or expected.has(sp.Integral):
                return False, {"rule": "trigonometric_integrate", "integrand": str(integrand), "_status_override": VerificationStatus.UNVERIFIED.value}, [], "UNVERIFIED: trigonometric integration remained unevaluated."
            residual = sp.simplify(sp.diff(actual, x) - integrand)
            equivalence = residual.equals(0) if hasattr(residual, "equals") else residual == 0
            backend_residual = sp.simplify(sp.diff(expected, x) - integrand)
            backend_equivalence = backend_residual.equals(0) if hasattr(backend_residual, "equals") else backend_residual == 0
        except Exception as exc:
            return False, {"rule": "trigonometric_integrate"}, [], f"UNVERIFIED: trigonometric integration could not be established: {type(exc).__name__}: {exc}"
        details = {
            "rule": "trigonometric_integrate", "variable": str(x), "integrand": str(integrand),
            "expected_result": str(expected), "actual_result": str(actual),
            "residual": str(residual), "backend_residual": str(backend_residual),
            "method": "sympy.manualintegrate", "verification": "differentiate_candidate_and_backend_result",
        }
        if equivalence is False or backend_equivalence is False:
            return False, details, [], "FAIL: trigonometric antiderivative is incorrect."
        if equivalence is not True or backend_equivalence is not True:
            details["_status_override"] = VerificationStatus.UNVERIFIED.value
            return False, details, [], "UNVERIFIED: symbolic trigonometric comparison could not establish equality."
        return True, details, [
            {"step": 1, "operation": "manualintegrate", "result": str(expected)},
            {"step": 2, "operation": "differentiate_backend_result", "residual": str(backend_residual)},
            {"step": 3, "operation": "differentiate_candidate", "residual": str(residual)},
        ], None

    # ------------------------------------------------------------------
    # Rule: nested_integrate
    # Verifies a represented sequence of indefinite integrations. The
    # sequence is explicit: variables are applied from left to right to
    # the integrand, and the proposed final expression is differentiated
    # back in reverse order. This supports mixed/repeated variables
    # without an arbitrary depth ceiling.
    # ------------------------------------------------------------------
    @classmethod
    def _verify_nested_integrate(
        cls, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variables = params.get("variables")
        if not isinstance(variables, list) or not variables:
            return False, {"rule": "nested_integrate"}, [], "Malformed nested integration: parameters['variables'] must be a non-empty list."
        if any(not isinstance(v, str) or not v.strip() or not v.strip().isidentifier() for v in variables):
            return False, {"rule": "nested_integrate", "variables": variables}, [], "Malformed nested integration variable list."
        parser = SafeParser()
        try:
            integrand = parser.parse(in_node.expression.raw_str)
            actual = parser.parse(out_node.expression.raw_str)
            symbols = [parser.make_symbol(v.strip()) for v in variables]
        except SafeParseError as exc:
            return False, {"rule": "nested_integrate", "variables": variables}, [], f"SafeParser rejected nested integration expression: {exc}"

        try:
            expected = integrand
            forward_steps = []
            for symbol in symbols:
                expected = sp.integrate(expected, symbol)
                forward_steps.append(str(expected))
                if isinstance(expected, sp.Integral) or expected.has(sp.Integral):
                    return (
                        False,
                        {"rule": "nested_integrate", "variables": [str(v) for v in symbols], "_status_override": VerificationStatus.UNVERIFIED.value},
                        [
                            {"step": i + 1, "operation": f"integrate_d{v}", "result": result}
                            for i, (v, result) in enumerate(zip(symbols, forward_steps))
                        ],
                        f"UNVERIFIED: integration with respect to {symbol} remained unevaluated."
                    )

            recovered = actual
            reverse_steps = []
            for symbol in reversed(symbols):
                recovered = sp.diff(recovered, symbol)
                reverse_steps.append(str(recovered))
            residual = sp.simplify(recovered - integrand)
            equivalence = residual.equals(0) if hasattr(residual, "equals") else (residual == 0)
        except Exception as exc:
            return (
                False,
                {"rule": "nested_integrate", "variables": [str(v) for v in symbols]},
                [],
                f"UNVERIFIED: nested integration could not be established: {type(exc).__name__}: {exc}"
            )

        if residual == 0 or equivalence is True:
            passed, override, error = True, None, None
        elif equivalence is False:
            passed, override = False, None
            error = f"Nested integral mismatch: expected a valid antiderivative chain, got {actual}."
        else:
            passed, override = False, VerificationStatus.UNVERIFIED.value
            error = "UNVERIFIED: nested integration comparison could not establish equality."

        details = {
            "rule": "nested_integrate",
            "variables": [str(v) for v in symbols],
            "integrand": str(integrand),
            "expected_result": str(expected),
            "actual_result": str(actual),
            "recovered_integrand": str(recovered),
            "residual": str(residual),
            "integration_depth": len(symbols),
            "forward_steps": forward_steps,
            "reverse_steps": reverse_steps,
        }
        if override:
            details["_status_override"] = override
        steps = [
            {"step": i + 1, "operation": f"integrate_d{symbol}", "result": result}
            for i, (symbol, result) in enumerate(zip(symbols, forward_steps))
        ]
        steps.extend(
            {"step": len(steps) + i + 1, "operation": f"differentiate_d{symbol}", "result": result}
            for i, (symbol, result) in enumerate(zip(reversed(symbols), reverse_steps))
        )
        return passed, details, steps, error

    # ------------------------------------------------------------------
    # Rule: substitute
    # Verifies that out_expr == in_expr with `from_expr` replaced by `to_expr`.
    # Parameters: {"from": "<expr>", "to": "<expr>"}
    # ------------------------------------------------------------------
    def _verify_substitute(
        self, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        from_str = params.get("from", "")
        to_str   = params.get("to", "")
        if not from_str or not to_str:
            return False, {"rule": "substitute"}, [], \
                "UNSUPPORTED: edge.parameters['from'] and ['to'] required for substitute rule."
        parser = SafeParser()
        try:
            in_expr   = parser.parse(in_node.expression.raw_str)
            out_expr  = parser.parse(out_node.expression.raw_str)
            from_expr = parser.parse(str(from_str))
            to_expr   = parser.parse(str(to_str))
        except SafeParseError as e:
            return False, {"rule": "substitute"}, [], f"SafeParser error: {e}"

        substituted = in_expr.subs(from_expr, to_expr)
        diff = sp.simplify(out_expr - substituted)
        passed = (diff == 0)
        details = {
            "in_expr": str(in_expr),
            "from": str(from_expr),
            "to": str(to_expr),
            "substituted": str(substituted),
            "actual_out": str(out_expr),
            "diff": str(diff),
        }
        steps = [
            {"step": 1, "operation": f"in_expr.subs({from_expr}, {to_expr})", "expr": str(substituted)},
            {"step": 2, "operation": "simplify(actual - substituted)", "expr": str(diff)},
        ]
        err = None if passed else f"substitute mismatch: expected {substituted}, got {out_expr}"
        return passed, details, steps, err

    # ------------------------------------------------------------------
    # Rule: simplify
    # Verifies that sp.simplify(in_expr) == out_expr.
    # This checks that the claimed simplified form is actually equivalent.
    # ------------------------------------------------------------------
    def _verify_simplify(
        self, in_node: Any, out_node: Any
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        parser = SafeParser()
        try:
            in_expr  = parser.parse(in_node.expression.raw_str)
            out_expr = parser.parse(out_node.expression.raw_str)
        except SafeParseError as e:
            return False, {"rule": "simplify"}, [], f"SafeParser error: {e}"

        # The claim is that in_expr and out_expr are algebraically equivalent
        # (simplify is not unique, so we check equivalence, not canonical form)
        diff = sp.simplify(in_expr - out_expr)
        passed = (diff == 0)
        details = {
            "in_expr": str(in_expr),
            "out_expr": str(out_expr),
            "diff": str(diff),
            "equivalent": passed,
        }
        steps = [{"step": 1, "operation": "simplify(in - out)", "expr": str(diff)}]
        err = None if passed else f"simplify: expressions are not equivalent: {diff}"
        return passed, details, steps, err


    # ------------------------------------------------------------------
    # Rules: limit / continuity
    # Limits are deliberately evaluated with explicit direction semantics.
    # A two-sided finite-point limit is established only when the left and
    # right limits both exist and agree. Direct substitution is never used
    # as a substitute for the limiting operation.
    # ------------------------------------------------------------------
    @staticmethod
    def _limit_assumption_symbols(raw: Any) -> Dict[str, sp.Symbol]:
        assumptions = raw or {}
        if not isinstance(assumptions, dict):
            raise ValueError("parameters['assumptions'] must be an object mapping symbol names to assumption names.")
        allowed = {"real", "positive", "negative", "nonzero", "integer"}
        symbols: Dict[str, sp.Symbol] = {}
        for name, assumption in assumptions.items():
            if not isinstance(name, str) or not name.isidentifier():
                raise ValueError("Assumption symbol names must be valid identifiers.")
            items = assumption if isinstance(assumption, list) else [assumption]
            props = {}
            for item in items:
                if item not in allowed:
                    raise ValueError(f"Unsupported symbolic assumption '{item}'.")
                props[item] = True
            symbols[name] = sp.Symbol(name, **props)
        return symbols

    @classmethod
    def _parse_limit_inputs(cls, in_node: Any, params: Dict[str, Any]) -> tuple[sp.Expr, sp.Symbol, sp.Expr, str]:
        from automate.ir.safe_parser import SafeParser, SafeParseError
        variable_name = params.get("variable", params.get("wrt", ""))
        if not isinstance(variable_name, str) or not variable_name.strip() or not variable_name.strip().isidentifier():
            raise ValueError("parameters['variable'] must be a valid identifier.")
        assumptions = cls._limit_assumption_symbols(params.get("assumptions"))
        variable = assumptions.get(variable_name, sp.Symbol(variable_name, real=True))
        parser = SafeParser(extra_symbols=assumptions | {variable_name: variable})
        try:
            expr = parser.parse(in_node.expression.raw_str)
        except SafeParseError as exc:
            raise ValueError(f"SafeParser rejected limit expression: {exc}") from exc
        point_raw = params.get("point")
        if point_raw is None:
            raise ValueError("parameters['point'] is required.")
        try:
            point = parser.parse(str(point_raw))
        except SafeParseError as exc:
            raise ValueError(f"SafeParser rejected limit point: {exc}") from exc
        direction = params.get("direction", "two_sided")
        if direction in {"-", "left"}:
            direction = "left"
        elif direction in {"+", "right"}:
            direction = "right"
        elif direction in {"two-sided", "both", "+-"}:
            direction = "two_sided"
        elif direction in {"infinity", "+infinity", "plus_infinity"}:
            direction = "+infinity"
        elif direction in {"-infinity", "minus_infinity"}:
            direction = "-infinity"
        elif direction not in {"two_sided", "left", "right"}:
            raise ValueError("Unsupported limit direction. Use two_sided, left, right, +infinity, or -infinity.")
        if direction in {"two_sided", "left", "right"} and point in {sp.oo, -sp.oo}:
            raise ValueError("Finite-point limit directions require a finite target point.")
        if direction == "+infinity":
            point = sp.oo
        elif direction == "-infinity":
            point = -sp.oo
        return expr, variable, point, direction

    @staticmethod
    def _limit_known(value: sp.Expr) -> bool:
        if isinstance(value, sp.Limit) or value is None:
            return False
        if value in {sp.nan, sp.zoo}:
            return False
        return not bool(value.has(sp.Limit))

    @classmethod
    def _limit_numeric_evidence(cls, expr: sp.Expr, variable: sp.Symbol, point: sp.Expr,
                                direction: str, expected: Any) -> Dict[str, Any]:
        """Independent NumPy sampling; evidence only, never the proof."""
        if expr.free_symbols - {variable}:
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Numeric limit evidence requires no unresolved symbols besides the limit variable."}
        if point not in {sp.oo, -sp.oo} and point.free_symbols:
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Numeric limit evidence requires a numeric target point."}
        try:
            fn = sp.lambdify(variable, expr, "numpy")
            if point in {sp.oo, -sp.oo}:
                samples = np.asarray([10.0, 30.0, 100.0, 300.0, 1000.0])
                if point == -sp.oo:
                    samples = -samples
            else:
                p = float(sp.N(point))
                deltas = np.asarray([1e-2, 3e-3, 1e-3, 3e-4, 1e-4])
                if direction == "left":
                    samples = p - deltas
                elif direction == "right":
                    samples = p + deltas
                else:
                    samples = np.concatenate([p - deltas, p + deltas])
            values = np.asarray(fn(samples), dtype=np.complex128).reshape(-1)
            finite_mask = np.isfinite(values.real) & np.isfinite(values.imag)
            samples = samples[finite_mask]
            values = values[finite_mask]
            if values.size == 0:
                return {"available": False, "independence_class": "NOT_AVAILABLE",
                        "reason": "Numeric sampling produced no finite sample values."}
            expected_value = None
            if expected != "DNE":
                try:
                    expected_value = complex(sp.N(expected))
                except Exception:
                    expected_value = None
            if expected_value is not None and np.isfinite(expected_value.real) and np.isfinite(expected_value.imag):
                scale = max(1.0, abs(expected_value))
                error = float(np.max(np.abs(values - expected_value)))
                passed = error <= 2e-3 + 2e-3 * scale
            elif expected == sp.oo:
                passed, error = bool(abs(values[-1]) > max(10.0, abs(values[0]) * 1.5)), None
            elif expected == -sp.oo:
                passed, error = bool(values[-1].real < min(-10.0, values[0].real * 1.5)), None
            else:
                passed, error = None, None
            return {
                "available": True, "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.lambdify_sampling", "version": np.__version__,
                "operation": "limit", "direction": direction,
                "sample_count": int(values.size), "sample_points": samples.tolist(),
                "sample_values": [str(complex(v)) for v in values],
                "passed": passed, "max_abs_error": error, "evidence_only": True,
            }
        except (TypeError, ValueError, OverflowError, ZeroDivisionError, FloatingPointError):
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Independent numerical limit sampling failed."}

    @classmethod
    def _limit_domain_supported(cls, expr: sp.Expr, variable: sp.Symbol, point: sp.Expr,
                                direction: str) -> tuple[bool, str]:
        """Conservatively require an approach path in the real scalar domain."""
        if point in {sp.oo, -sp.oo}:
            return True, "infinite_target"
        if point.free_symbols:
            if all(symbol.is_real is True for symbol in point.free_symbols):
                return True, "symbolic_real_target_under_explicit_assumptions"
            return False, "symbolic target is not established as real; add an explicit real assumption."
        extra_symbols = expr.free_symbols - {variable}
        if extra_symbols:
            if all(symbol.is_real is True for symbol in extra_symbols):
                return True, "explicitly_real_symbolic_parameters"
            return False, "symbolic parameter domain is not established as real."
        try:
            from sympy.calculus.util import continuous_domain
            domain = continuous_domain(expr, variable, sp.S.Reals)
            punctured = sp.Complement(sp.S.Reals, sp.FiniteSet(point))
            if domain == punctured:
                return True, "punctured_real_domain"
            if direction in {"two_sided", "left"}:
                left = sp.Interval.open(point - 1, point)
                if left.is_subset(domain) is not True:
                    if direction == "left":
                        return False, f"real-domain analysis did not establish a left punctured neighborhood: {domain}"
                    return False, f"real-domain analysis did not establish a left punctured neighborhood: {domain}"
            if direction in {"two_sided", "right"}:
                right = sp.Interval.open(point, point + 1)
                if right.is_subset(domain) is not True:
                    return False, f"real-domain analysis did not establish a right punctured neighborhood: {domain}"
            return True, str(domain)
        except (NotImplementedError, ValueError, TypeError):
            return False, "real-domain analysis was unavailable"
    
    @staticmethod
    def _ftc_zero_state(expr: sp.Expr) -> Optional[bool]:
        try:
            reduced = sp.simplify(expr)
        except Exception:
            return None
        if reduced == 0 or reduced.is_zero is True:
            return True
        if reduced.is_zero is False:
            return False
        try:
            result = reduced.equals(0)
        except Exception:
            return None
        return result if result in (True, False) else None

    @classmethod
    def _verify_fundamental_theorem(
        cls,
        in_nodes: List[Any],
        out_nodes: List[Any],
        params: Dict[str, Any],
    ):
        from automate.ir.safe_parser import SafeParser, SafeParseError

        mode = params.get("mode", "evaluation")
        if mode not in {"evaluation", "accumulation_derivative"}:
            return False, {"rule": "fundamental_theorem_calculus", "mode": mode}, [], \
                "Unsupported FTC mode; use 'evaluation' or 'accumulation_derivative'."
        if len(in_nodes) != 2 or len(out_nodes) != 1:
            return False, {"rule": "fundamental_theorem_calculus", "mode": mode}, [], \
                "FTC requires two inputs and one scalar output claim."

        variable_name = params.get("variable", "")
        integration_name = params.get("integration_variable", variable_name)
        if not isinstance(variable_name, str) or not variable_name.strip().isidentifier():
            return False, {"rule": "fundamental_theorem_calculus"}, [], \
                "parameters['variable'] must be a valid identifier."
        if not isinstance(integration_name, str) or not integration_name.strip().isidentifier():
            return False, {"rule": "fundamental_theorem_calculus"}, [], \
                "parameters['integration_variable'] must be a valid identifier."
        if mode == "accumulation_derivative" and variable_name.strip() == integration_name.strip():
            return False, {"rule": "fundamental_theorem_calculus"}, [], \
                "accumulation_derivative mode requires distinct differentiation and integration variables."

        variable = sp.Symbol(variable_name.strip(), real=True)
        integration_variable = sp.Symbol(integration_name.strip(), real=True)
        parser = SafeParser(extra_symbols={
            variable_name.strip(): variable,
            integration_name.strip(): integration_variable,
        })

        lower_raw = params.get("lower")
        if lower_raw is None:
            return False, {"rule": "fundamental_theorem_calculus", "mode": mode}, [], \
                "parameters['lower'] is required."
        try:
            integrand = parser.parse(in_nodes[0].expression.raw_str)
            candidate_function = parser.parse(in_nodes[1].expression.raw_str)
            output = parser.parse(out_nodes[0].expression.raw_str)
            lower = parser.parse(str(lower_raw))
        except SafeParseError as exc:
            return False, {"rule": "fundamental_theorem_calculus", "mode": mode}, [], \
                f"SafeParser rejected FTC expression: {exc}"

        if lower.has(variable) or lower.has(integration_variable):
            return False, {"rule": "fundamental_theorem_calculus", "lower": str(lower)}, [], \
                "FTC lower bound must be independent of theorem variables."
        extra_integrand_symbols = integrand.free_symbols - {integration_variable}
        if mode == "accumulation_derivative":
            extra_integrand_symbols -= {variable}
        if extra_integrand_symbols:
            return False, {"rule": "fundamental_theorem_calculus", "integrand": str(integrand)}, [], \
                "FTC integrand contains undeclared free variables."

        details = {
            "rule": "fundamental_theorem_calculus",
            "mode": mode,
            "variable": str(variable),
            "integration_variable": str(integration_variable),
            "lower": str(lower),
            "integrand": str(integrand),
            "candidate_function": str(candidate_function),
            "continuity_obligation": "ftc_integrand_continuous_on_interval",
        }

        if mode == "accumulation_derivative":
            integrand_at_x = integrand.xreplace({integration_variable: variable})
            derivative = sp.diff(candidate_function, variable)
            derivative_residual = sp.simplify(derivative - integrand_at_x)
            anchor_residual = sp.simplify(candidate_function.subs(variable, lower))
            derivative_zero = cls._ftc_zero_state(derivative_residual)
            anchor_zero = cls._ftc_zero_state(anchor_residual)
            if derivative_zero is False:
                return False, {**details, "derivative_residual": str(derivative_residual)}, [], \
                    "FTC Part I failed: F'(x) does not equal f(x)."
            if anchor_zero is False:
                return False, {**details, "anchor_residual": str(anchor_residual)}, [], \
                    "FTC Part I failed: the accumulation function does not satisfy F(lower) = 0."
            if derivative_zero is None or anchor_zero is None:
                return False, {**details,
                               "derivative_residual": str(derivative_residual),
                               "anchor_residual": str(anchor_residual),
                               "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                    "FTC Part I could not establish its required identities exactly."
            candidate_residual = sp.simplify(output - integrand_at_x)
            candidate_zero = cls._ftc_zero_state(candidate_residual)
            if candidate_zero is False:
                return False, {**details,
                               "expected_derivative": str(integrand_at_x),
                               "claimed_derivative": str(output),
                               "candidate_residual": str(candidate_residual)}, [], \
                    "FTC Part I derivative claim does not equal f(x)."
            if candidate_zero is None:
                return False, {**details,
                               "expected_derivative": str(integrand_at_x),
                               "claimed_derivative": str(output),
                               "candidate_residual": str(candidate_residual),
                               "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                    "FTC Part I derivative claim comparison remained unresolved."
            details.update({
                "expected_derivative": str(integrand_at_x),
                "claimed_derivative": str(output),
                "derivative_residual": str(derivative_residual),
                "anchor_residual": str(anchor_residual),
                "candidate_residual": str(candidate_residual),
            })
            steps = [
                {"step": 1, "operation": "verify_F_prime_equals_f_x", "residual": str(derivative_residual)},
                {"step": 2, "operation": "verify_F_lower_equals_zero", "residual": str(anchor_residual)},
                {"step": 3, "operation": "verify_claimed_derivative", "residual": str(candidate_residual)},
            ]
            return True, details, steps, None

        upper_raw = params.get("upper")
        if upper_raw is None:
            return False, {**details}, [], \
                "parameters['upper'] is required for FTC evaluation mode."
        try:
            upper = parser.parse(str(upper_raw))
        except SafeParseError as exc:
            return False, {**details}, [], f"SafeParser rejected FTC upper bound: {exc}"
        if upper.has(integration_variable):
            return False, {**details, "upper": str(upper)}, [], \
                "FTC upper bound must be independent of the integration variable."
        derivative = sp.diff(candidate_function, integration_variable)
        derivative_residual = sp.simplify(derivative - integrand)
        derivative_zero = cls._ftc_zero_state(derivative_residual)
        if derivative_zero is False:
            return False, {**details, "upper": str(upper), "derivative_residual": str(derivative_residual)}, [], \
                "FTC Part II failed: the supplied antiderivative does not differentiate to the integrand."
        if derivative_zero is None:
            return False, {**details, "upper": str(upper), "derivative_residual": str(derivative_residual),
                           "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                "FTC Part II antiderivative identity remained unresolved."
        expected_value = sp.simplify(
            candidate_function.subs(integration_variable, upper)
            - candidate_function.subs(integration_variable, lower)
        )
        candidate_residual = sp.simplify(output - expected_value)
        candidate_zero = cls._ftc_zero_state(candidate_residual)
        if candidate_zero is False:
            return False, {**details,
                           "upper": str(upper),
                           "expected_integral": str(expected_value),
                           "claimed_integral": str(output),
                           "candidate_residual": str(candidate_residual)}, [], \
                "FTC Part II result does not equal F(upper) - F(lower)."
        if candidate_zero is None:
            return False, {**details,
                           "upper": str(upper),
                           "expected_integral": str(expected_value),
                           "claimed_integral": str(output),
                           "candidate_residual": str(candidate_residual),
                           "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                "FTC Part II result comparison remained unresolved."
        details.update({
            "upper": str(upper),
            "expected_integral": str(expected_value),
            "claimed_integral": str(output),
            "derivative_residual": str(derivative_residual),
            "candidate_residual": str(candidate_residual),
        })
        steps = [
            {"step": 1, "operation": "verify_F_prime_equals_f", "residual": str(derivative_residual)},
            {"step": 2, "operation": "evaluate_F_at_bounds", "lower": str(lower), "upper": str(upper)},
            {"step": 3, "operation": "verify_integral_equals_Fb_minus_Fa", "residual": str(candidate_residual)},
        ]
        return True, details, steps, None

    @classmethod
    def _verify_limit(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        from automate.ir.safe_parser import SafeParser, SafeParseError
        expr, variable, point, direction = cls._parse_limit_inputs(in_node, params)
        expected_raw = out_node.expression.raw_str.strip()
        if not expected_raw:
            return False, {"rule": "limit"}, [], "Malformed limit result."
        if expected_raw.upper() in {"DNE", "DOES_NOT_EXIST", "NONEXISTENT"}:
            expected_marker, expected = "DNE", "DNE"
        else:
            expected_symbols = cls._limit_assumption_symbols(params.get("assumptions"))
            expected_symbols[str(variable)] = variable
            parser = SafeParser(extra_symbols=expected_symbols)
            try:
                expected = parser.parse(expected_raw)
            except SafeParseError as exc:
                return False, {"rule": "limit"}, [], f"SafeParser rejected claimed limit: {exc}"
            expected_marker = None
        try:
            domain_ok, domain_detail = cls._limit_domain_supported(expr, variable, point, direction)
            if not domain_ok:
                return False, {"rule": "limit", "direction": direction, "variable": str(variable),
                               "point": str(point), "domain_analysis": domain_detail,
                               "_status_override": VerificationStatus.UNVERIFIED.value}, [],                        "Limit domain/approach path could not be established safely."
            if direction == "two_sided":
                left = sp.limit(expr, variable, point, dir="-")
                right = sp.limit(expr, variable, point, dir="+")
                if not cls._limit_known(left) or not cls._limit_known(right):
                    return False, {"rule": "limit", "direction": direction, "variable": str(variable),
                                   "point": str(point), "left_limit": str(left), "right_limit": str(right),
                                   "_status_override": VerificationStatus.UNVERIFIED.value}, \
                           "Two-sided limit could not be established from both one-sided limits."
                if isinstance(left, sp.AccumBounds) or isinstance(right, sp.AccumBounds):
                    actual, existence = "DNE", "nonexistent"
                elif left == right:
                    actual, existence = left, "finite_or_infinite"
                else:
                    actual, existence = "DNE", "nonexistent"
            else:
                sympy_dir = "-" if direction == "left" else "+" if direction == "right" else "+"
                actual = sp.limit(expr, variable, point, dir=sympy_dir)
                if not cls._limit_known(actual):
                    return False, {"rule": "limit", "direction": direction, "variable": str(variable),
                                   "point": str(point), "computed_limit": str(actual),
                                   "_status_override": VerificationStatus.UNVERIFIED.value}, \
                           "Limit computation remained unresolved."
                existence = "finite" if actual.is_finite is True else "infinite" if actual in {sp.oo, -sp.oo} else "undetermined"
            if expected_marker == "DNE":
                passed = actual == "DNE"
                error_msg = None if passed else f"Limit exists as {actual}; claimed DNE."
            else:
                if actual == expected:
                    passed, error_msg = True, None
                else:
                    comparison = sp.simplify(actual - expected) if actual != "DNE" else sp.Integer(1)
                    if comparison == 0:
                        passed, error_msg = True, None
                    elif getattr(comparison, "is_zero", None) is False or comparison.is_number:
                        passed, error_msg = False, f"Limit mismatch: expected {expected}, computed {actual}."
                    else:
                        return False, {"rule": "limit", "direction": direction, "variable": str(variable),
                                       "point": str(point), "computed_limit": str(actual), "claimed_limit": str(expected),
                                       "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                               "Limit comparison depends on unresolved symbolic assumptions."
            numeric = cls._limit_numeric_evidence(expr, variable, point, direction, actual)
            details = {"rule": "limit", "direction": direction, "variable": str(variable), "point": str(point),
                       "computed_limit": str(actual), "claimed_limit": expected_raw,
                       "existence_class": existence, "domain_analysis": domain_detail,
                       "numeric_evidence": numeric}
            steps = [{"step": 1, "operation": "compute explicit directional limit", "direction": direction},
                     {"step": 2, "operation": "compare computed limit with claimed result",
                      "computed": str(actual), "claimed": expected_raw}]
            return passed, details, steps, error_msg
        except (NotImplementedError, ValueError, TypeError, ZeroDivisionError) as exc:
            return False, {"rule": "limit", "direction": direction,
                           "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                   f"UNVERIFIED: limit computation unavailable: {type(exc).__name__}: {exc}"

    @classmethod
    def _verify_continuity(cls, in_node: Any, out_node: Any, params: Dict[str, Any]):
        expr, variable, point, direction = cls._parse_limit_inputs(in_node, params)
        if direction != "two_sided" or point in {sp.oo, -sp.oo}:
            return False, {"rule": "continuity"}, [], \
                "UNSUPPORTED: continuity is pointwise at a finite ordinary point; use limit for one-sided or infinite targets."

        domain_ok, domain_detail = cls._limit_domain_supported(expr, variable, point, "two_sided")
        value = expr.subs(variable, point)
        value_defined = value not in {sp.nan, sp.zoo, sp.oo, -sp.oo} and not value.has(sp.zoo, sp.nan)

        # Continuity is defined through the two-sided limit, so compute the
        # same left/right obligations used by the limit rule even when f(a)
        # itself is undefined (the removable-discontinuity case).
        if not domain_ok:
            return False, {"rule": "continuity", "function_value": str(value),
                           "function_value_defined": value_defined,
                           "domain_analysis": domain_detail,
                           "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                   "Continuity could not be established because the real approach domain is unresolved."
        else:
            left = sp.limit(expr, variable, point, dir="-")
            right = sp.limit(expr, variable, point, dir="+")
            if not cls._limit_known(left) or not cls._limit_known(right):
                return False, {"rule": "continuity", "function_value": str(value),
                               "function_value_defined": value_defined,
                               "left_limit": str(left), "right_limit": str(right),
                               "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                       "Continuity could not be established because the two-sided limit is unresolved."
            if not value_defined:
                actual_indicator = 0
            elif isinstance(left, sp.AccumBounds) or isinstance(right, sp.AccumBounds):
                actual_indicator = 0
            elif left != right:
                actual_indicator = 0
            else:
                difference = sp.simplify(left - value)
                if difference == 0:
                    actual_indicator = 1
                elif difference.is_zero is False or difference.is_number:
                    actual_indicator = 0
                else:
                    return False, {"rule": "continuity", "function_value": str(value),
                                   "two_sided_limit": str(left),
                                   "domain_analysis": domain_detail,
                                   "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                           "Continuity comparison depends on unresolved symbolic assumptions."

        expected_raw = out_node.expression.raw_str.strip()
        if expected_raw not in {"0", "1"}:
            return False, {"rule": "continuity", "function_value": str(value)}, [], \
                   "Continuity output must be the explicit indicator 1 (continuous) or 0 (not continuous)."
        passed = int(expected_raw) == actual_indicator
        details = {
            "rule": "continuity",
            "variable": str(variable),
            "point": str(point),
            "function_value": str(value),
            "function_value_defined": value_defined,
            "left_limit": str(left) if left is not None else None,
            "right_limit": str(right) if right is not None else None,
            "two_sided_limit": str(left) if left is not None and left == right else "DNE",
            "continuous_indicator": actual_indicator,
            "domain_analysis": domain_detail,
            "interpretation": "1 means lim(x->a) f(x) = f(a); 0 means continuity is not established.",
        }
        if value_defined and left is not None and left == right:
            details["numeric_evidence"] = cls._limit_numeric_evidence(expr, variable, point, "two_sided", left)
        else:
            details["numeric_evidence"] = {
                "available": False, "independence_class": "NOT_AVAILABLE",
                "reason": "Independent numeric evidence is not decisive for an undefined value or nonexistent two-sided limit.",
                "evidence_only": True,
            }
        steps = [
            {"step": 1, "operation": "evaluate function value at the point", "value": str(value)},
            {"step": 2, "operation": "compute left and right limits",
             "left": str(left) if left is not None else None,
             "right": str(right) if right is not None else None},
            {"step": 3, "operation": "verify lim(x->a) f(x) = f(a)"},
        ]
        return passed, details, steps, None if passed else \
               f"Continuity mismatch: expected indicator {expected_raw}, computed {actual_indicator}"


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
