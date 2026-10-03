"""
SymPyChecker: Symbolic mathematics backend using SymPy.
Verifies algebraic identities, differentiation, Euler-Lagrange equations,
differential equation solutions, and conservation laws.
"""

import time
import re
from typing import Dict, Any, List, Optional, Tuple
import sympy as sp
from sympy.core.function import AppliedUndef

from automate.backend.sympy_utils import safe_parse_expr
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
                    passed, details, certificates, error_msg = self._verify_harmonic_solution(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule in {"simplify", "algebraic_identity"}:
                    passed, details, certificates, error_msg = self._verify_algebraic_identity(
                        in_nodes[0], out_nodes[0]
                    )
                elif rule == "differentiate_both_sides":
                    passed, details, certificates, error_msg = self._verify_differentiate(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "substitute":
                    passed, details, certificates, error_msg = self._verify_substitute(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "divide_both_sides":
                    passed, details, certificates, error_msg = self._verify_divide(
                        in_nodes[0], out_nodes[0], edge.parameters, edge.side_conditions, graph
                    )
                else:
                    passed = False
                    details = {"rule": rule}
                    error_msg = f"Unsupported symbolic transformation rule: {rule}"
            except Exception as e:
                passed = False
                error_msg = f"SymPy computation error: {type(e).__name__}: {str(e)}"

            status = VerificationStatus.SYMBOLIC_CHECKED if passed else VerificationStatus.FAILED

        elapsed = (time.perf_counter() - start_time) * 1000

        # Update edge certificate if passed
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


    @staticmethod
    def _relation_residual(raw_str: str, locals_map: Dict[str, Any]) -> Tuple[sp.Expr, Optional[str]]:
        """Parse an expression/equality into a SymPy residual and relation."""
        text = raw_str.strip()
        for relation in ("<=", ">=", "!=", "=", "<", ">"):
            if relation in text:
                lhs_text, rhs_text = text.split(relation, 1)
                lhs = SymPyChecker._parse_expression(lhs_text.strip(), locals_map)
                rhs = SymPyChecker._parse_expression(rhs_text.strip(), locals_map)
                return sp.simplify(lhs - rhs), relation
        return safe_parse_expr(text, locals_map=locals_map), None

    @staticmethod
    def _build_context(params: Dict[str, Any]) -> Dict[str, Any]:
        """Build one consistent symbolic context for all graph expressions."""
        time_name = str(params.get("time_variable", "t"))
        coordinate_name = str(params.get("coordinate", "x"))
        t = sp.Symbol(time_name, real=True)
        q = sp.Function(coordinate_name)(t)
        local: Dict[str, Any] = {
            time_name: t,
            coordinate_name: q,
            f"{coordinate_name}_dot": sp.diff(q, t),
            f"{coordinate_name}_ddot": sp.diff(q, t, 2),
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "exp": sp.exp,
            "log": sp.log,
            "sqrt": sp.sqrt,
            "pi": sp.pi,
        }
        for name, assumptions in (
            ("m", {"positive": True}),
            ("k", {"positive": True}),
            ("A", {"real": True}),
            ("phi", {"real": True}),
            ("omega", {"positive": True}),
            ("E", {"real": True}),
        ):
            local.setdefault(name, sp.Symbol(name, **assumptions))
        for name, value in params.items():
            if isinstance(value, (int, float)):
                local[name] = sp.Float(value)
        return local

    @staticmethod
    def _parse_expression(raw_str: str, locals_map: Dict[str, Any]) -> sp.Expr:
        text = raw_str.strip()
        coordinate = next(
            (name for name, value in locals_map.items()
             if isinstance(value, AppliedUndef)),
            None,
        )
        time_symbol = "t"
        if coordinate and isinstance(locals_map.get(coordinate), AppliedUndef):
            if locals_map[coordinate].args:
                time_symbol = str(locals_map[coordinate].args[0])
        if coordinate:
            text = re.sub(
                rf"\bdiff\(\s*{re.escape(coordinate)}\(\s*{re.escape(time_symbol)}\s*\)\s*,\s*{re.escape(time_symbol)}\s*,\s*2\s*\)",
                f"{coordinate}_ddot",
                text,
            )
            text = re.sub(
                rf"\bdiff\(\s*{re.escape(coordinate)}\(\s*{re.escape(time_symbol)}\s*\)\s*,\s*{re.escape(time_symbol)}\s*\)",
                f"{coordinate}_dot",
                text,
            )
            text = re.sub(
                rf"\b{re.escape(coordinate)}\(\s*{re.escape(time_symbol)}\s*\)",
                coordinate,
                text,
            )
            text = text.replace(f"{coordinate}_dot_dot", f"{coordinate}_ddot")
        return safe_parse_expr(text, locals_map=locals_map)


    def _parse_relation_sides(
        self, raw_str: str, locals_map: Dict[str, Any]
    ) -> Tuple[sp.Expr, Optional[str], Optional[sp.Expr]]:
        text = raw_str.strip()
        for relation in ("<=", ">=", "!=", "=", "<", ">"):
            if relation in text:
                lhs_text, rhs_text = text.split(relation, 1)
                return (
                    self._parse_expression(lhs_text.strip(), locals_map),
                    relation,
                    self._parse_expression(rhs_text.strip(), locals_map),
                )
        return self._parse_expression(text, locals_map), None, None

    def _verify_differentiate(
        self, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        local = self._build_context(params)
        variable_name = str(params.get("wrt", params.get("time_variable", "t")))
        variable = local.get(variable_name)
        if variable is None:
            variable = sp.Symbol(variable_name, real=True)
            local[variable_name] = variable

        in_lhs, in_relation, in_rhs = self._parse_relation_sides(in_node.expression.raw_str, local)
        out_lhs, out_relation, out_rhs = self._parse_relation_sides(out_node.expression.raw_str, local)

        if in_relation != out_relation:
            return False, {}, [], "Differentiation requires input and output to use the same relation type."

        if in_relation == "=":
            expected_lhs = sp.simplify(sp.diff(in_lhs, variable))
            expected_rhs = sp.simplify(sp.diff(in_rhs, variable))
            residual = sp.simplify((out_lhs - expected_lhs) - (out_rhs - expected_rhs))
            passed = residual == 0
            details = {
                "variable": variable_name,
                "expected_lhs": str(expected_lhs),
                "expected_rhs": str(expected_rhs),
                "output_lhs": str(out_lhs),
                "output_rhs": str(out_rhs),
                "difference": str(residual),
            }
        else:
            expected = sp.simplify(sp.diff(in_lhs, variable))
            residual = sp.simplify(out_lhs - expected)
            passed = residual == 0
            details = {
                "variable": variable_name,
                "expected_derivative": str(expected),
                "output": str(out_lhs),
                "difference": str(residual),
            }

        steps = [{
            "step": 1,
            "operation": f"d/d{variable_name}",
            "expr": str(residual),
            "latex": sp.latex(residual),
        }]
        error = None if passed else f"Differentiation result mismatch: residual {residual}"
        return passed, details, steps, error

    def _verify_substitute(
        self, in_node: Any, out_node: Any, params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        local = self._build_context(params)
        symbol_name = params.get("symbol", params.get("target"))
        replacement_text = params.get("replacement", params.get("value"))
        if symbol_name is None or replacement_text is None:
            return False, {}, [], "Substitution requires parameters 'symbol' and 'replacement'."

        symbol_name = str(symbol_name)
        target = local.get(symbol_name)
        if target is None:
            target = sp.Symbol(symbol_name, real=True)
            local[symbol_name] = target
        replacement = safe_parse_expr(str(replacement_text), locals_map=local)

        in_lhs, in_relation, in_rhs = self._parse_relation_sides(in_node.expression.raw_str, local)
        out_lhs, out_relation, out_rhs = self._parse_relation_sides(out_node.expression.raw_str, local)
        if in_relation != out_relation:
            return False, {}, [], "Substitution requires matching input and output relation types."

        expected_lhs = sp.simplify(in_lhs.subs(target, replacement))
        if in_relation == "=":
            expected_rhs = sp.simplify(in_rhs.subs(target, replacement))
            residual = sp.simplify((out_lhs - expected_lhs) - (out_rhs - expected_rhs))
        else:
            expected_rhs = None
            residual = sp.simplify(out_lhs - expected_lhs)

        passed = residual == 0
        details = {
            "symbol": symbol_name,
            "replacement": str(replacement),
            "difference": str(residual),
        }
        steps = [{
            "step": 1,
            "operation": "substitute",
            "expr": str(replacement),
            "latex": sp.latex(replacement),
        }, {
            "step": 2,
            "operation": "simplify_difference",
            "expr": str(residual),
            "latex": sp.latex(residual),
        }]
        error = None if passed else f"Substitution result mismatch: residual {residual}"
        return passed, details, steps, error

    def _verify_divide(
        self, in_node: Any, out_node: Any, params: Dict[str, Any],
        side_conditions: List[str], graph: DerivationGraph
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        local = self._build_context(params)
        divisor_text = params.get("divisor")
        if divisor_text is None:
            return False, {}, [], "Division requires parameter 'divisor'."
        divisor = safe_parse_expr(str(divisor_text), locals_map=local)

        nonzero = sp.ask(sp.Q.nonzero(divisor))
        if nonzero is not True:
            divisor_key = str(divisor).replace(" ", "")
            for aid in side_conditions:
                asm = graph.assumptions.get(aid)
                if asm and asm.active:
                    pred = asm.formal_predicate.replace(" ", "")
                    if (
                        f"{divisor_key}!=0" in pred
                        or f"{divisor_key}>0" in pred
                        or f"{divisor_key}<0" in pred
                    ):
                        nonzero = True
                        break
        if nonzero is not True:
            return False, {
                "divisor": str(divisor),
                "nonzero_status": str(nonzero),
            }, [], "Division requires proof that the divisor is non-zero."

        in_lhs, in_relation, in_rhs = self._parse_relation_sides(in_node.expression.raw_str, local)
        out_lhs, out_relation, out_rhs = self._parse_relation_sides(out_node.expression.raw_str, local)
        if in_relation != "=" or out_relation != "=":
            return False, {}, [], "Divide-both-sides requires input and output equations."

        expected_lhs = sp.simplify(in_lhs / divisor)
        expected_rhs = sp.simplify(in_rhs / divisor)
        lhs_error = sp.simplify(out_lhs - expected_lhs)
        rhs_error = sp.simplify(out_rhs - expected_rhs)
        passed = lhs_error == 0 and rhs_error == 0

        details = {
            "divisor": str(divisor),
            "nonzero_status": True,
            "input": f"{in_lhs} = {in_rhs}",
            "expected_output": f"{expected_lhs} = {expected_rhs}",
            "output": f"{out_lhs} = {out_rhs}",
            "lhs_difference": str(lhs_error),
            "rhs_difference": str(rhs_error),
        }
        steps = [{
            "step": 1,
            "operation": "divide_lhs",
            "expr": str(expected_lhs),
            "latex": sp.latex(expected_lhs),
        }, {
            "step": 2,
            "operation": "divide_rhs",
            "expr": str(expected_rhs),
            "latex": sp.latex(expected_rhs),
        }]
        error = None if passed else (
            f"Divide-both-sides result mismatch: lhs residual {lhs_error}, rhs residual {rhs_error}"
        )
        return passed, details, steps, error

    def _verify_euler_lagrange(
        self, lagr_node: Any, eom_node: Any, params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """Verify Euler-Lagrange from the graph's actual Lagrangian and EoM."""
        local = self._build_context(params)
        time_name = str(params.get("time_variable", "t"))
        coordinate_name = str(params.get("coordinate", "x"))
        t = local[time_name]
        q = local[coordinate_name]
        q_dot = sp.diff(q, t)

        L = self._parse_expression(lagr_node.expression.raw_str, local)
        target_residual, relation = self._relation_residual(eom_node.expression.raw_str, local)
        dL_dqdot = sp.diff(L, q_dot)
        ddt_dL_dqdot = sp.diff(dL_dqdot, t)
        dL_dq = sp.diff(L, q)
        computed_residual = sp.simplify(ddt_dL_dqdot - dL_dq)
        difference = sp.simplify(computed_residual - target_residual)
        passed = relation in (None, "=") and difference == 0

        steps = [
            {"step": 1, "operation": "dL/dq_dot", "expr": str(dL_dqdot), "latex": sp.latex(dL_dqdot)},
            {"step": 2, "operation": "d/dt(dL/dq_dot)", "expr": str(ddt_dL_dqdot), "latex": sp.latex(ddt_dL_dqdot)},
            {"step": 3, "operation": "dL/dq", "expr": str(dL_dq), "latex": sp.latex(dL_dq)},
            {"step": 4, "operation": "Euler-Lagrange residual", "expr": str(computed_residual), "latex": sp.latex(computed_residual)},
        ]
        details = {
            "lagrangian": str(L),
            "computed_eom": str(computed_residual),
            "target_eom_residual": str(target_residual),
            "difference": str(difference),
            "relation": relation,
            "zero_test_passed": passed,
        }
        error = None if passed else (
            f"Euler-Lagrange residual mismatch: computed {computed_residual}, "
            f"target {target_residual}, difference {difference}"
        )
        return passed, details, steps, error

    def _verify_energy_conservation(
        self, in_nodes: List[Any], energy_node: Any, params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """Verify conservation using the graph's actual energy and EoM."""
        local = self._build_context(params)
        time_name = str(params.get("time_variable", "t"))
        coordinate_name = str(params.get("coordinate", "x"))
        t = local[time_name]
        q_ddot = sp.diff(local[coordinate_name], t, 2)

        eom_node = next((node for node in in_nodes if "=" in node.expression.raw_str), None)
        if eom_node is None:
            return False, {}, [], "Energy conservation requires an input equation of motion."

        eom_residual, relation = self._relation_residual(eom_node.expression.raw_str, local)
        if relation != "=":
            return False, {}, [], "Energy conservation requires an equality equation of motion."

        energy_text = energy_node.expression.raw_str.strip()
        if "=" in energy_text:
            lhs_text, rhs_text = energy_text.split("=", 1)
            lhs = self._parse_expression(lhs_text, local)
            rhs = self._parse_expression(rhs_text, local)
            E_symbol = local["E"]
            if sp.simplify(lhs - E_symbol) == 0:
                E = rhs
            elif sp.simplify(rhs - E_symbol) == 0:
                E = lhs
            else:
                E = rhs
        else:
            E = self._parse_expression(energy_text, local)

        dE_dt = sp.simplify(sp.diff(E, t))
        solutions = sp.solve(eom_residual, q_ddot, dict=True)
        if not solutions:
            return False, {"energy": str(E), "dE_dt": str(dE_dt)}, [], (
                "Could not solve the supplied equation of motion for acceleration."
            )

        on_shell_candidates = [sp.simplify(dE_dt.subs(sol)) for sol in solutions]
        on_shell = on_shell_candidates[0]
        passed = all(candidate == 0 for candidate in on_shell_candidates)

        steps = [
            {"step": 1, "operation": "dE/dt", "expr": str(dE_dt), "latex": sp.latex(dE_dt)},
            {"step": 2, "operation": "solve_eom_for_acceleration", "expr": str(solutions[0][q_ddot]), "latex": sp.latex(solutions[0][q_ddot])},
            {"step": 3, "operation": "substitute_eom", "expr": str(on_shell), "latex": sp.latex(on_shell)},
        ]
        details = {
            "energy": str(E),
            "eom_residual": str(eom_residual),
            "dE_dt": str(dE_dt),
            "dE_dt_on_shell": str(on_shell),
            "solutions_for_acceleration": [str(sol[q_ddot]) for sol in solutions],
            "is_conserved": passed,
        }
        error = None if passed else f"Energy derivative is not zero on the supplied EoM: {on_shell}"
        return passed, details, steps, error

    def _verify_harmonic_solution(
        self, eom_node: Any, sol_node: Any, params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """Verify the proposed solution against the supplied graph EoM."""
        local = self._build_context(params)
        time_name = str(params.get("time_variable", "t"))
        coordinate_name = str(params.get("coordinate", "x"))
        t = local[time_name]
        q = local[coordinate_name]
        omega = local["omega"]

        eom_residual, relation = self._relation_residual(eom_node.expression.raw_str, local)
        if relation != "=":
            return False, {}, [], "Harmonic solution requires an equality equation of motion."

        solution_text = sol_node.expression.raw_str.strip()
        if "=" not in solution_text:
            return False, {}, [], "Harmonic solution node must contain an equality."
        lhs_text, rhs_text = solution_text.split("=", 1)
        solution_lhs = self._parse_expression(lhs_text, local)
        proposed = self._parse_expression(rhs_text, local)

        if sp.simplify(solution_lhs - q) != 0:
            return False, {
                "solution_lhs": str(solution_lhs),
                "expected_lhs": str(q),
            }, [], "Solution node does not solve for the configured coordinate."

        x_dot_candidate = sp.diff(proposed, t)
        x_ddot_candidate = sp.diff(proposed, t, 2)
        substituted = sp.simplify(
            eom_residual.subs({
                q: proposed,
                sp.diff(q, t): x_dot_candidate,
                sp.diff(q, t, 2): x_ddot_candidate,
            })
        )

        frequency_definition = None
        if substituted != 0 and omega in proposed.free_symbols:
            omega_value = params.get("omega")
            if omega_value is None:
                omega_value_expr = sp.sqrt(local["k"] / local["m"])
                frequency_definition = "omega = sqrt(k/m) derived from the supplied harmonic EoM"
            else:
                omega_value_expr = self._parse_expression(str(omega_value), local)
            substituted = sp.simplify(substituted.subs(omega, omega_value_expr))

        passed = substituted == 0
        steps = [
            {"step": 1, "operation": "proposed_solution", "expr": str(proposed), "latex": sp.latex(proposed)},
            {"step": 2, "operation": "dx/dt", "expr": str(x_dot_candidate), "latex": sp.latex(x_dot_candidate)},
            {"step": 3, "operation": "d2x/dt2", "expr": str(x_ddot_candidate), "latex": sp.latex(x_ddot_candidate)},
            {"step": 4, "operation": "substitute_solution_into_eom", "expr": str(substituted), "latex": sp.latex(substituted)},
        ]
        details = {
            "equation_residual": str(eom_residual),
            "solution": str(proposed),
            "residual": str(substituted),
            "satisfies_ode": passed,
        }
        if frequency_definition:
            details["frequency_definition"] = frequency_definition
        error = None if passed else f"Harmonic solution residual is non-zero: {substituted}"
        return passed, details, steps, error

    def _verify_algebraic_identity(
        self, in_node: Any, out_node: Any
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        expr1 = safe_parse_expr(in_node.expression.raw_str)
        expr2 = safe_parse_expr(out_node.expression.raw_str)
        diff = sp.simplify(expr1 - expr2)
        passed = (diff == 0)
        details = {"diff": str(diff), "equal": passed}
        steps = [{"step": 1, "operation": "simplify(expr1 - expr2)", "expr": str(diff)}]
        return passed, details, steps, None if passed else f"Expressions are not algebraically identical: {diff}"
