"""
Generalized Classical Lagrangian & Hamiltonian Mechanics Engine for Automate.
Handles arbitrary 1D and multi-coordinate Lagrangians, generalized coordinates
(Cartesian, polar, angles), canonical momenta, Hamiltonians, and Noether conservation laws.
Operates directly on symbolic graph semantics without hardcoded solutions.
"""

from typing import Dict, Any, List, Optional, Tuple, Set, Union
import sympy as sp


class LagrangianSystem:
    """
    Represents a classical mechanical system defined by generalized coordinates and a Lagrangian.
    """

    def __init__(
        self,
        lagrangian: Union[str, sp.Expr],
        coordinates: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        time_symbol: str = "t"
    ):
        self.time_sym = sp.Symbol(time_symbol, real=True)
        self.coord_names = list(coordinates)
        self.param_dict = parameters or {}

        # Build symbol table
        self.symbols: Dict[str, sp.Symbol] = {}
        for p_name, p_props in self.param_dict.items():
            if isinstance(p_props, dict):
                pos = p_props.get("positive", False)
                real = p_props.get("real", True)
                self.symbols[p_name] = sp.Symbol(p_name, positive=pos, real=real)
            elif p_props == "positive":
                self.symbols[p_name] = sp.Symbol(p_name, positive=True, real=True)
            else:
                self.symbols[p_name] = sp.Symbol(p_name, real=True)

        # Coordinate functions of time: q(t), dot_q(t), ddot_q(t)
        self.q_funcs: Dict[str, sp.Expr] = {}
        self.q_dots: Dict[str, sp.Expr] = {}
        self.q_ddots: Dict[str, sp.Expr] = {}

        # Dummy algebraic symbols for partial differentiation
        self.q_syms: Dict[str, sp.Symbol] = {}
        self.v_syms: Dict[str, sp.Symbol] = {}
        self.a_syms: Dict[str, sp.Symbol] = {}

        for q in self.coord_names:
            q_f = sp.Function(q)(self.time_sym)
            qd_f = sp.diff(q_f, self.time_sym)
            qdd_f = sp.diff(qd_f, self.time_sym)

            self.q_funcs[q] = q_f
            self.q_dots[q] = qd_f
            self.q_ddots[q] = qdd_f

            self.q_syms[q] = sp.Symbol(q, real=True)
            self.v_syms[q] = sp.Symbol(f"{q}_dot", real=True)
            self.a_syms[q] = sp.Symbol(f"{q}_ddot", real=True)

        self.lagrangian = self._parse_expression(lagrangian)

    def _parse_expression(self, expr_in: Union[str, sp.Expr]) -> sp.Expr:
        """
        Parses an expression string into a SymPy expression in terms of q(t) and diff(q(t), t).
        """
        if isinstance(expr_in, sp.Expr):
            return expr_in

        # Build local symbol dict for parsing
        local_dict: Dict[str, Any] = {self.time_sym.name: self.time_sym}
        local_dict.update(self.symbols)

        for q in self.coord_names:
            # Map function name 'x' to function x(t)
            local_dict[q] = self.q_funcs[q]
            local_dict[f"{q}_dot"] = self.q_dots[q]
            local_dict[f"{q}_ddot"] = self.q_ddots[q]

        # Use SymPy parse_expr with custom local dict
        parsed = sp.sympify(expr_in, locals=local_dict)

        # Ensure any bare symbols q are converted to q(t) if appropriate
        subs_map = {}
        for q in self.coord_names:
            bare_q = sp.Symbol(q)
            if bare_q in parsed.free_symbols and bare_q != self.q_funcs[q]:
                subs_map[bare_q] = self.q_funcs[q]
            bare_v = sp.Symbol(f"{q}_dot")
            if bare_v in parsed.free_symbols:
                subs_map[bare_v] = self.q_dots[q]

        if subs_map:
            parsed = parsed.subs(subs_map)

        return parsed

    def to_algebraic(self, expr: sp.Expr) -> sp.Expr:
        """Converts q(t), diff(q(t), t), diff(q(t), t, 2) into dummy symbols q, q_dot, q_ddot."""
        subs_map = {}
        for q in self.coord_names:
            subs_map[self.q_ddots[q]] = self.a_syms[q]
            subs_map[self.q_dots[q]] = self.v_syms[q]
            subs_map[self.q_funcs[q]] = self.q_syms[q]
        return expr.subs(subs_map)

    def to_time_dependent(self, expr: sp.Expr) -> sp.Expr:
        """Converts dummy symbols q, q_dot, q_ddot back to q(t), diff(q(t), t), diff(q(t), t, 2)."""
        subs_map = {}
        for q in self.coord_names:
            subs_map[self.a_syms[q]] = self.q_ddots[q]
            subs_map[self.v_syms[q]] = self.q_dots[q]
            subs_map[self.q_syms[q]] = self.q_funcs[q]
        return expr.subs(subs_map)

    def canonical_momenta(self) -> Dict[str, sp.Expr]:
        """
        Computes canonical momenta p_i = dL/d(dot_q_i).
        """
        L_alg = self.to_algebraic(self.lagrangian)
        momenta = {}
        for q in self.coord_names:
            p_alg = sp.diff(L_alg, self.v_syms[q])
            momenta[q] = sp.simplify(self.to_time_dependent(p_alg))
        return momenta

    def euler_lagrange_equations(self) -> Tuple[Dict[str, sp.Expr], List[Dict[str, Any]]]:
        """
        Calculates d/dt(dL/d(dot_q_i)) - dL/dq_i = 0 for all coordinates.
        Returns dictionary of LHS expressions (equated to 0) and micro-step certificates.
        """
        L_alg = self.to_algebraic(self.lagrangian)
        eoms: Dict[str, sp.Expr] = {}
        steps: List[Dict[str, Any]] = []

        step_idx = 1
        for q in self.coord_names:
            # 1. dL / d(q_dot)
            dL_dv = sp.diff(L_alg, self.v_syms[q])
            dL_dqdot = self.to_time_dependent(dL_dv)
            steps.append({
                "step": step_idx,
                "operation": f"dL/d({q}_dot)",
                "coordinate": q,
                "expr": str(dL_dqdot),
                "latex": sp.latex(dL_dqdot)
            })
            step_idx += 1

            # 2. d/dt (dL / d(q_dot))
            ddt_dL_dqdot = sp.diff(dL_dqdot, self.time_sym)
            steps.append({
                "step": step_idx,
                "operation": f"d/dt(dL/d({q}_dot))",
                "coordinate": q,
                "expr": str(ddt_dL_dqdot),
                "latex": sp.latex(ddt_dL_dqdot)
            })
            step_idx += 1

            # 3. dL / dq
            dL_du = sp.diff(L_alg, self.q_syms[q])
            dL_dq = self.to_time_dependent(dL_du)
            steps.append({
                "step": step_idx,
                "operation": f"dL/d({q})",
                "coordinate": q,
                "expr": str(dL_dq),
                "latex": sp.latex(dL_dq)
            })
            step_idx += 1

            # 4. E_i = d/dt(dL/d(dot_q_i)) - dL/dq_i
            eom_lhs = sp.simplify(ddt_dL_dqdot - dL_dq)
            eoms[q] = eom_lhs
            steps.append({
                "step": step_idx,
                "operation": f"Euler-Lagrange LHS ({q})",
                "coordinate": q,
                "expr": str(eom_lhs),
                "latex": sp.latex(eom_lhs)
            })
            step_idx += 1

        return eoms, steps

    def verify_euler_lagrange(
        self,
        candidate_eom_str: Union[str, Dict[str, str]]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Verifies that candidate equation(s) of motion match the Euler-Lagrange equations derived from L.
        """
        computed_eoms, steps = self.euler_lagrange_equations()

        candidate_eoms: Dict[str, sp.Expr] = {}
        if isinstance(candidate_eom_str, dict):
            for q, c_str in candidate_eom_str.items():
                candidate_eoms[q] = self._parse_equation_lhs(c_str)
        else:
            # Single equation string
            if len(self.coord_names) == 1:
                q0 = self.coord_names[0]
                candidate_eoms[q0] = self._parse_equation_lhs(candidate_eom_str)
            else:
                return False, {}, steps, "System has multiple coordinates; provide candidate EoMs as a dictionary."

        all_passed = True
        diffs: Dict[str, str] = {}
        for q, comp_lhs in computed_eoms.items():
            cand_lhs = candidate_eoms.get(q)
            if cand_lhs is None:
                return False, {}, steps, f"Missing candidate equation of motion for coordinate '{q}'"

            # Check if comp_lhs == cand_lhs or if they are proportional by non-zero constant
            diff = sp.simplify(comp_lhs - cand_lhs)
            if diff == 0:
                diffs[q] = "0 (exact identity)"
            else:
                # Check proportionality (e.g. m*x_ddot + k*x = 0 vs x_ddot + (k/m)*x = 0)
                ratio = sp.simplify(comp_lhs / cand_lhs)
                if ratio != 0 and ratio.free_symbols.issubset(set(self.symbols.values())):
                    diffs[q] = f"proportional by factor {ratio}"
                else:
                    all_passed = False
                    diffs[q] = str(diff)

        details = {
            "computed_eoms": {q: str(e) for q, e in computed_eoms.items()},
            "candidate_eoms": {q: str(e) for q, e in candidate_eoms.items()},
            "residuals": diffs,
            "all_passed": all_passed
        }

        err = None if all_passed else f"Euler-Lagrange residual mismatch: {diffs}"
        return all_passed, details, steps, err

    def _parse_equation_lhs(self, eq_str: str) -> sp.Expr:
        """Parses an equation string 'A = B' into LHS - RHS, or 'A' directly."""
        if "=" in eq_str:
            parts = eq_str.split("=")
            lhs = self._parse_expression(parts[0].strip())
            rhs = self._parse_expression(parts[1].strip())
            return sp.simplify(lhs - rhs)
        return self._parse_expression(eq_str)

    def hamiltonian(self) -> Tuple[sp.Expr, Dict[str, sp.Symbol]]:
        """
        Constructs the Hamiltonian H(q, p) via Legendre transform H = sum(p_i * v_i) - L.
        Inverts p_i = dL/dv_i for v_i where possible.
        """
        L_alg = self.to_algebraic(self.lagrangian)
        p_syms = {q: sp.Symbol(f"p_{q}", real=True) for q in self.coord_names}

        # Momenta definitions: p_i = dL/dv_i
        momenta_eqs = [sp.Eq(p_syms[q], sp.diff(L_alg, self.v_syms[q])) for q in self.coord_names]

        # Solve for v_i in terms of p_i, q_i
        v_list = [self.v_syms[q] for q in self.coord_names]
        sol = sp.solve(momenta_eqs, v_list, dict=True)

        if not sol:
            raise ValueError("Legendre transform singular: cannot invert velocities in terms of canonical momenta.")

        v_subs = sol[0]
        H_alg = sum(p_syms[q] * v_subs[self.v_syms[q]] for q in self.coord_names) - L_alg.subs(v_subs)
        return sp.simplify(H_alg), p_syms

    def check_noether_conservation(self) -> Dict[str, Any]:
        """
        Analyzes Lagrangian symmetries and returns conserved quantities:
        - Cyclic coordinates (Noether linear/angular momentum conservation)
        - Time translation invariance (Hamiltonian/energy conservation)
        """
        L_alg = self.to_algebraic(self.lagrangian)
        conserved = []

        # 1. Coordinate translation invariance (cyclic coordinates)
        for q in self.coord_names:
            dL_dq = sp.simplify(sp.diff(L_alg, self.q_syms[q]))
            if dL_dq == 0:
                p_i = sp.diff(L_alg, self.v_syms[q])
                conserved.append({
                    "symmetry": f"Translation invariance in {q}",
                    "conserved_quantity": f"Canonical momentum p_{q}",
                    "expression": str(p_i),
                    "type": "momentum",
                    "coordinate": q
                })

        # 2. Explicit time translation invariance: partial L / partial t == 0
        dL_dt_explicit = sp.simplify(sp.diff(L_alg, self.time_sym))
        time_independent = (dL_dt_explicit == 0)
        if time_independent:
            momenta = self.canonical_momenta()
            # E = sum(p_i * q_dot_i) - L
            E = sum(momenta[q] * self.q_dots[q] for q in self.coord_names) - self.lagrangian
            conserved.append({
                "symmetry": "Explicit time translation invariance",
                "conserved_quantity": "Jacobi energy function E",
                "expression": str(sp.simplify(E)),
                "type": "energy"
            })

        return {
            "time_independent": time_independent,
            "conserved_quantities": conserved
        }

    def verify_energy_conservation(
        self,
        candidate_energy_str: str,
        candidate_eom_str: Optional[Union[str, Dict[str, str]]] = None
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Verifies that dE/dt = 0 along the solutions of the equations of motion.
        Works for arbitrary 1D and multi-coordinate systems.
        """
        E = self._parse_expression(candidate_energy_str)

        # 1. dE/dt
        dE_dt = sp.diff(E, self.time_sym)
        steps = [{
            "step": 1,
            "operation": "dE/dt",
            "expr": str(dE_dt),
            "latex": sp.latex(dE_dt)
        }]

        # 2. Extract accelerations from equations of motion
        eoms, _ = self.euler_lagrange_equations()
        accel_subs = {}
        for q in self.coord_names:
            # Solve eom[q] == 0 for q_ddot
            sol = sp.solve(eoms[q], self.q_ddots[q])
            if sol:
                accel_subs[self.q_ddots[q]] = sol[0]

        steps.append({
            "step": 2,
            "operation": "solve_accelerations_from_eom",
            "substitutions": {str(k): str(v) for k, v in accel_subs.items()}
        })

        # 3. Substitute on-shell accelerations into dE/dt
        dE_dt_on_shell = sp.simplify(dE_dt.subs(accel_subs))
        steps.append({
            "step": 3,
            "operation": "dE/dt_on_shell",
            "expr": str(dE_dt_on_shell),
            "latex": sp.latex(dE_dt_on_shell)
        })

        passed = (dE_dt_on_shell == 0)
        details = {
            "candidate_energy": str(E),
            "dE_dt_raw": str(dE_dt),
            "dE_dt_on_shell": str(dE_dt_on_shell),
            "conserved": passed
        }

        err = None if passed else f"Total time derivative of energy is non-zero on-shell: {dE_dt_on_shell}"
        return passed, details, steps, err
