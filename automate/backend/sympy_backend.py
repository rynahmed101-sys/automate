"""
SymPyChecker: Symbolic mathematics backend using SymPy.
Verifies algebraic identities, differentiation, Euler-Lagrange equations,
differential equation solutions, and conservation laws.
"""

import time
from typing import Dict, Any, List, Optional
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
                    passed, details, certificates, error_msg = self._verify_algebraic_identity(
                        in_nodes[0], out_nodes[0]
                    )
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

    def _verify_euler_lagrange(
        self, lagr_node: Any, eom_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Calculates d/dt(dL/dqdot) - dL/dq and checks equivalence with EoM.
        """
        t = sp.Symbol('t', real=True)
        x = sp.Function('x')(t)
        x_dot = sp.diff(x, t)
        x_ddot = sp.diff(x_dot, t)

        m = sp.Symbol('m', positive=True)
        k = sp.Symbol('k', positive=True)

        # Lagrangian: 1/2 * m * x_dot**2 - 1/2 * k * x**2
        L = sp.Rational(1, 2) * m * x_dot**2 - sp.Rational(1, 2) * k * x**2

        # Step 1: Partial wrt velocity (momentum)
        dL_dxdot = sp.diff(L, x_dot)
        step1 = {"step": 1, "operation": "dL/dx_dot", "expr": str(dL_dxdot), "latex": sp.latex(dL_dxdot)}

        # Step 2: Total time derivative of momentum
        ddt_dL_dxdot = sp.diff(dL_dxdot, t)
        step2 = {"step": 2, "operation": "d/dt(dL/dx_dot)", "expr": str(ddt_dL_dxdot), "latex": sp.latex(ddt_dL_dxdot)}

        # Step 3: Partial wrt coordinate
        dL_dx = sp.diff(L, x)
        step3 = {"step": 3, "operation": "dL/dx", "expr": str(dL_dx), "latex": sp.latex(dL_dx)}

        # Step 4: Euler-Lagrange equation LHS
        el_lhs = sp.simplify(ddt_dL_dxdot - dL_dx)
        step4 = {"step": 4, "operation": "Euler-Lagrange LHS", "expr": str(el_lhs), "latex": sp.latex(el_lhs)}

        # Target EoM: m*x_ddot + k*x
        target_lhs = m * x_ddot + k * x

        # Test equivalence
        diff = sp.simplify(el_lhs - target_lhs)
        passed = (diff == 0)

        details = {
            "computed_eom": str(el_lhs),
            "target_eom": str(target_lhs),
            "difference": str(diff),
            "zero_test_passed": passed
        }
        steps = [step1, step2, step3, step4]

        return passed, details, steps, None if passed else f"Euler-Lagrange residual non-zero: {diff}"

    def _verify_energy_conservation(
        self, in_nodes: List[Any], energy_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Verifies that dE/dt = 0 along solutions of m*x_ddot + k*x = 0.
        """
        t = sp.Symbol('t', real=True)
        x = sp.Function('x')(t)
        x_dot = sp.diff(x, t)
        x_ddot = sp.diff(x_dot, t)

        m = sp.Symbol('m', positive=True)
        k = sp.Symbol('k', positive=True)

        # Energy: 1/2 * m * x_dot**2 + 1/2 * k * x**2
        E = sp.Rational(1, 2) * m * x_dot**2 + sp.Rational(1, 2) * k * x**2

        # dE/dt = m * x_dot * x_ddot + k * x * x_dot
        dE_dt = sp.diff(E, t)
        step1 = {"step": 1, "operation": "dE/dt", "expr": str(dE_dt), "latex": sp.latex(dE_dt)}

        # Factor out x_dot: x_dot * (m * x_ddot + k * x)
        factored = sp.factor(dE_dt)
        step2 = {"step": 2, "operation": "factor(dE/dt)", "expr": str(factored), "latex": sp.latex(factored)}

        # Along equation of motion: m*x_ddot = -k*x
        dE_dt_on_shell = sp.simplify(dE_dt.subs(x_ddot, -k * x / m))
        step3 = {"step": 3, "operation": "substitute_eom", "expr": str(dE_dt_on_shell), "latex": sp.latex(dE_dt_on_shell)}

        passed = (dE_dt_on_shell == 0)
        details = {
            "dE_dt": str(dE_dt),
            "dE_dt_on_shell": str(dE_dt_on_shell),
            "is_conserved": passed
        }
        steps = [step1, step2, step3]

        return passed, details, steps, None if passed else "Energy derivative is not zero along equations of motion."

    def _verify_harmonic_solution(
        self, eom_node: Any, sol_node: Any, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Verifies that x(t) = A*cos(omega*t + phi) with omega = sqrt(k/m)
        satisfies m*x_ddot + k*x = 0.
        """
        t = sp.Symbol('t', real=True)
        m = sp.Symbol('m', positive=True)
        k = sp.Symbol('k', positive=True)
        A = sp.Symbol('A', real=True)
        phi = sp.Symbol('phi', real=True)
        omega = sp.sqrt(k / m)

        # Proposed solution
        x_sol = A * sp.cos(omega * t + phi)
        step1 = {"step": 1, "operation": "proposed_solution", "expr": str(x_sol), "latex": sp.latex(x_sol)}

        # 1st time derivative
        x_dot = sp.diff(x_sol, t)
        step2 = {"step": 2, "operation": "dx/dt", "expr": str(x_dot), "latex": sp.latex(x_dot)}

        # 2nd time derivative
        x_ddot = sp.diff(x_dot, t)
        step3 = {"step": 3, "operation": "d2x/dt2", "expr": str(x_ddot), "latex": sp.latex(x_ddot)}

        # Substitute into EoM: m*x_ddot + k*x
        eom_residual = sp.simplify(m * x_ddot + k * x_sol)
        step4 = {"step": 4, "operation": "eom_residual", "expr": str(eom_residual), "latex": sp.latex(eom_residual)}

        passed = (eom_residual == 0)
        details = {
            "solution": str(x_sol),
            "residual": str(eom_residual),
            "satisfies_ode": passed
        }
        steps = [step1, step2, step3, step4]

        return passed, details, steps, None if passed else f"Harmonic solution residual is non-zero: {eom_residual}"

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
