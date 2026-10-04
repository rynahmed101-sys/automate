"""
Symbolic Variational Calculus & Field Theory Engine for Automate.
Performs functional variation of actions S = integral d^D x L(phi, partial_mu phi, x^mu)
to derive Euler-Lagrange field equations:
    delta S / delta phi_a = partial L / partial phi_a - partial_mu ( partial L / partial (partial_mu phi_a) ) = 0.
"""

from typing import Dict, Any, List, Optional, Tuple, Set, Union
import sympy as sp


class FieldTheoryAction:
    """
    Represents a classical field theory action with continuous spacetime symmetries
    and field functional derivatives.
    """

    def __init__(
        self,
        lagrangian_density: Union[str, sp.Expr],
        fields: List[str],
        coordinates: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metric_signature: str = "(-,+,+,+)"
    ):
        self.field_names = list(fields)
        self.coord_names = list(coordinates) if coordinates else ["t", "x", "y", "z"]
        self.signature = metric_signature
        self.param_dict = parameters or {}

        # Spacetime coordinate symbols
        self.coord_syms = [sp.Symbol(c, real=True) for c in self.coord_names]
        self.coord_map = {c: s for c, s in zip(self.coord_names, self.coord_syms)}

        # Parameters
        self.symbols: Dict[str, sp.Symbol] = {}
        for p_name, p_props in self.param_dict.items():
            if p_props == "positive":
                self.symbols[p_name] = sp.Symbol(p_name, positive=True, real=True)
            else:
                self.symbols[p_name] = sp.Symbol(p_name, real=True)

        # Field functions of spacetime coordinates: phi(t, x, ...)
        self.field_funcs: Dict[str, sp.Expr] = {}
        self.field_grad: Dict[str, Dict[str, sp.Expr]] = {}

        # Dummy symbols for algebraic partial differentiation
        self.field_syms: Dict[str, sp.Symbol] = {}
        self.grad_syms: Dict[str, Dict[str, sp.Symbol]] = {}

        for f in self.field_names:
            f_func = sp.Function(f)(*self.coord_syms)
            self.field_funcs[f] = f_func
            self.field_syms[f] = sp.Symbol(f, real=True)

            self.field_grad[f] = {}
            self.grad_syms[f] = {}
            for c, c_sym in self.coord_map.items():
                self.field_grad[f][c] = sp.diff(f_func, c_sym)
                self.grad_syms[f][c] = sp.Symbol(f"d_{c}_{f}", real=True)

        self.lagrangian_density = self._parse_expression(lagrangian_density)

    def _parse_expression(self, expr_in: Union[str, sp.Expr]) -> sp.Expr:
        if isinstance(expr_in, sp.Expr):
            return expr_in

        local_dict: Dict[str, Any] = dict(self.coord_map)
        local_dict.update(self.symbols)

        for f in self.field_names:
            local_dict[f] = self.field_funcs[f]
            for c in self.coord_names:
                local_dict[f"d_{c}_{f}"] = self.field_grad[f][c]
                local_dict[f"diff({f}, {c})"] = self.field_grad[f][c]

        from automate.ir.safe_parser import SafeParser
        parsed = SafeParser(extra_symbols=local_dict).parse(expr_in)

        # Substitute bare symbols into field functions if needed
        subs_map = {}
        for f in self.field_names:
            bare_f = sp.Symbol(f)
            if bare_f in parsed.free_symbols and bare_f != self.field_funcs[f]:
                subs_map[bare_f] = self.field_funcs[f]

        if subs_map:
            parsed = parsed.subs(subs_map)

        return parsed

    def to_algebraic(self, expr: sp.Expr) -> sp.Expr:
        """Replaces field functions and gradients with dummy algebraic symbols."""
        subs_map = {}
        for f in self.field_names:
            subs_map[self.field_funcs[f]] = self.field_syms[f]
            for c in self.coord_names:
                subs_map[self.field_grad[f][c]] = self.grad_syms[f][c]
        return expr.subs(subs_map)

    def to_field_dependent(self, expr: sp.Expr) -> sp.Expr:
        """Replaces dummy algebraic symbols with field functions and spacetime derivatives."""
        subs_map = {}
        for f in self.field_names:
            subs_map[self.field_syms[f]] = self.field_funcs[f]
            for c in self.coord_names:
                subs_map[self.grad_syms[f][c]] = self.field_grad[f][c]
        return expr.subs(subs_map)

    def euler_lagrange_field_equations(self) -> Tuple[Dict[str, sp.Expr], List[Dict[str, Any]]]:
        """
        Derives the Euler-Lagrange field equation for each field phi_a:
            dL/dphi_a - sum_mu d/dx^mu ( dL / d(d_mu phi_a) ) = 0.
        """
        L_alg = self.to_algebraic(self.lagrangian_density)
        eoms: Dict[str, sp.Expr] = {}
        steps: List[Dict[str, Any]] = []

        step_idx = 1
        for f in self.field_names:
            # 1. dL / d(phi)
            dL_dphi_alg = sp.diff(L_alg, self.field_syms[f])
            dL_dphi = self.to_field_dependent(dL_dphi_alg)
            steps.append({
                "step": step_idx,
                "operation": f"dL/d({f})",
                "field": f,
                "expr": str(dL_dphi),
                "latex": sp.latex(dL_dphi)
            })
            step_idx += 1

            # 2. For each coordinate x^mu, compute Pi^mu = dL / d(d_mu phi)
            div_terms = []
            for c in self.coord_names:
                dL_dgrad_alg = sp.diff(L_alg, self.grad_syms[f][c])
                dL_dgrad = self.to_field_dependent(dL_dgrad_alg)

                # Spacetime divergence: d/dx^mu (Pi^mu)
                d_mu_Pi = sp.diff(dL_dgrad, self.coord_map[c])
                div_terms.append(d_mu_Pi)

                steps.append({
                    "step": step_idx,
                    "operation": f"d/d{c}(dL/d(d_{c}_{f}))",
                    "coordinate": c,
                    "field": f,
                    "expr": str(d_mu_Pi),
                    "latex": sp.latex(d_mu_Pi)
                })
                step_idx += 1

            # 3. Field Equation: dL/dphi - sum_mu d_mu(Pi^mu) = 0
            # (or sum_mu d_mu(Pi^mu) - dL/dphi = 0)
            total_div = sum(div_terms)
            field_eq_lhs = sp.simplify(total_div - dL_dphi)
            eoms[f] = field_eq_lhs

            steps.append({
                "step": step_idx,
                "operation": f"Euler-Lagrange Field Equation ({f})",
                "field": f,
                "expr": str(field_eq_lhs),
                "latex": sp.latex(field_eq_lhs)
            })
            step_idx += 1

        return eoms, steps

    def verify_field_equation(
        self,
        candidate_eq_str: Union[str, Dict[str, str]]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Verifies that candidate field equation(s) match the Euler-Lagrange equations derived from L.
        """
        computed_eoms, steps = self.euler_lagrange_field_equations()

        candidate_eoms: Dict[str, sp.Expr] = {}
        if isinstance(candidate_eq_str, dict):
            for f, c_str in candidate_eq_str.items():
                candidate_eoms[f] = self._parse_equation_lhs(c_str)
        else:
            if len(self.field_names) == 1:
                f0 = self.field_names[0]
                candidate_eoms[f0] = self._parse_equation_lhs(candidate_eq_str)
            else:
                return False, {}, steps, "Multiple fields present; provide candidate equations as dictionary."

        all_passed = True
        diffs = {}
        for f, comp_lhs in computed_eoms.items():
            cand_lhs = candidate_eoms.get(f)
            if cand_lhs is None:
                return False, {}, steps, f"Missing candidate field equation for field '{f}'"

            diff = sp.simplify(comp_lhs - cand_lhs)
            diff_neg = sp.simplify(comp_lhs + cand_lhs)

            if diff == 0:
                diffs[f] = "0 (exact identity)"
            elif diff_neg == 0:
                diffs[f] = "0 (sign-reversed identity)"
            else:
                all_passed = False
                diffs[f] = str(diff)

        details = {
            "computed_field_eoms": {f: str(e) for f, e in computed_eoms.items()},
            "candidate_field_eoms": {f: str(e) for f, e in candidate_eoms.items()},
            "residuals": diffs,
            "all_passed": all_passed
        }

        err = None if all_passed else f"Field equation residual non-zero: {diffs}"
        return all_passed, details, steps, err

    def _parse_equation_lhs(self, eq_str: str) -> sp.Expr:
        if "=" in eq_str:
            parts = eq_str.split("=")
            lhs = self._parse_expression(parts[0].strip())
            rhs = self._parse_expression(parts[1].strip())
            return sp.simplify(lhs - rhs)
        return self._parse_expression(eq_str)
