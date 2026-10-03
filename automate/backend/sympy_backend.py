"""
SymPyChecker: Symbolic mathematics backend using SymPy.
Verifies algebraic identities, differentiation, Euler-Lagrange equations,
differential equation solutions, and conservation laws.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
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
                    passed, details, certificates, error_msg = self._verify_harmonic_solution(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                elif rule == "algebraic_identity":
                    passed, details, certificates, error_msg = self._verify_algebraic_identity(
                        in_nodes[0], out_nodes[0]
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
                lhs = sp.sympify(lhs_text.strip(), locals=locals_map)
                rhs = sp.sympify(rhs_text.strip(), locals=locals_map)
                return sp.simplify(lhs - rhs), relation
        return sp.sympify(text, locals=locals_map), None

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
        return sp.sympify(raw_str.strip(), locals=locals_map)

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
        expr1 = sp.sympify(in_node.expression.raw_str)
        expr2 = sp.sympify(out_node.expression.raw_str)
        diff = sp.simplify(expr1 - expr2)
        passed = (diff == 0)
        details = {"diff": str(diff), "equal": passed}
        steps = [{"step": 1, "operation": "simplify(expr1 - expr2)", "expr": str(diff)}]
        return passed, details, steps, None if passed else f"Expressions are not algebraically identical: {diff}"
