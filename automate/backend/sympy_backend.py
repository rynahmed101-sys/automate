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
                elif rule == "substitute":
                    passed, details, certificates, error_msg = self._verify_substitute(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "simplify":
                    passed, details, certificates, error_msg = self._verify_simplify(
                        in_nodes[0], out_nodes[0]
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
            expected = sp.diff(outer, parser.make_symbol(str(params.get("inner_variable", "u")))) * sp.diff(inner, variable)
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
                    False, {"rule": "implicit_differentiate", "F_x": str(fx), "F_y": str(fy)}, [],
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
            if value_defined:
                return False, {"rule": "continuity", "function_value": str(value),
                               "domain_analysis": domain_detail,
                               "_status_override": VerificationStatus.UNVERIFIED.value}, [], \
                       "Continuity could not be established because the real approach domain is unresolved."
            actual_indicator = 0
            left = right = None
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
