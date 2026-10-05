"""Reusable ordinary-differential-equation reasoning helpers.

The ODE engine is deliberately representation/verification first: it parses
equations through SafeParser, derives structural information from the supplied
equation, and verifies proposed solutions by exact residual substitution.
SymPy is used as a computational backend, not as an unqualified semantic
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re

import sympy as sp

from automate.ir.safe_parser import SafeParser, SafeParseError
from sympy.core.function import AppliedUndef


@dataclass
class ODEResult:
    passed: bool
    status: str
    details: Dict[str, Any]
    steps: List[Dict[str, Any]]
    error: Optional[str] = None


class ODEEngine:
    """Reusable scalar/system ODE representation and verification engine."""

    def __init__(self, variable: str = "t", function: str = "y"):
        self.variable_name = variable
        self.function_name = function
        self.variable = sp.Symbol(variable, real=True)
        self.function = sp.Function(function)

    # ---------- safe parsing / representation ----------

    def _locals(self, function_names: Sequence[str] = ()) -> Dict[str, Any]:
        loc: Dict[str, Any] = {self.variable_name: self.variable}
        names = [self.function_name, *function_names]
        for name in names:
            if name and name not in loc:
                loc[name] = sp.Function(name)
        return loc

    def _normalize_shorthand_equation(self, text: str) -> str:
        """Lift legacy y_dot/y_ddot-style notation into function notation."""
        raw = str(text).strip()
        fn_call = f"{self.function_name}({self.variable_name})"
        if fn_call in raw or "diff(" in raw or "Derivative(" in raw:
            return raw
        escaped = re.escape(self.function_name)
        normalized = raw
        normalized = re.sub(rf"\b{escaped}_ddot\b", f"diff({self.function_name}({self.variable_name}), {self.variable_name}, 2)", normalized)
        normalized = re.sub(rf"\b{escaped}_dot\b", f"diff({self.function_name}({self.variable_name}), {self.variable_name})", normalized)
        normalized = re.sub(rf"\b{escaped}\b", f"{self.function_name}({self.variable_name})", normalized)
        return normalized

    def parse_expression(self, text: str, function_names: Sequence[str] = ()) -> sp.Expr:
        parser = SafeParser()
        return parser.parse(
            str(text).strip(),
            extra_locals=self._locals(function_names),
        )

    def parse_equation(self, text: str, function_names: Sequence[str] = ()) -> sp.Expr:
        parser = SafeParser()
        return parser.parse_equation(
            str(text).strip(),
            extra_locals=self._locals(function_names),
        )

    def parse_candidate(self, text: str) -> sp.Expr:
        return self.parse_expression(text)

    def parse_parameters(self, params: Dict[str, Any], key: str) -> sp.Expr:
        value = params.get(key)
        if value is None or str(value).strip() == "":
            raise SafeParseError(f"edge.parameters['{key}'] is required")
        return self.parse_expression(str(value))

    def _result(
        self,
        passed: bool,
        details: Dict[str, Any],
        steps: List[Dict[str, Any]],
        error: Optional[str] = None,
        unresolved: bool = False,
    ) -> ODEResult:
        if passed:
            status = "SYMBOLIC_CHECKED"
        elif unresolved:
            status = "UNVERIFIED"
        else:
            status = "FAILED"
        return ODEResult(passed, status, details, steps, error)

    def _zero_state(self, expr: sp.Expr) -> Optional[bool]:
        """Return True/False only when symbolic zero-ness is established."""
        try:
            reduced = sp.simplify(expr)
        except Exception:
            return None
        if reduced == 0 or reduced.is_zero is True:
            return True
        if reduced.is_zero is False:
            return False
        try:
            proved_zero = reduced.equals(0)
            if proved_zero is False:
                return False
            if proved_zero is True:
                return True
        except Exception:
            pass
        return None

    def _candidate_residual(
        self, equation: sp.Expr, candidate: sp.Expr
    ) -> Tuple[sp.Expr, int, Optional[bool]]:
        y = self.function(self.variable)
        derivatives = [
            d for d in equation.atoms(sp.Derivative)
            if d.expr == y and all(v == self.variable for v in d.variables)
        ]
        order = max([len(d.variables) for d in derivatives] + [0])

        substitutions: Dict[sp.Expr, sp.Expr] = {y: candidate}
        for n in range(order, 0, -1):
            substitutions[sp.diff(y, self.variable, n)] = sp.diff(
                candidate, self.variable, n
            )
        residual = equation.xreplace(substitutions)
        # xreplace may miss nested/non-identical function applications. A
        # second substitution pass is safe because all replacements are exact.
        residual = sp.simplify(residual.subs(substitutions))
        try:
            residual = sp.trigsimp(residual)
            residual = sp.simplify(residual)
        except Exception:
            pass
        return residual, order, self._zero_state(residual)

    def verify_solution(
        self, equation_text: str, candidate_text: str, params: Optional[Dict[str, Any]] = None
    ) -> ODEResult:
        params = params or {}
        try:
            normalized_equation = self._normalize_shorthand_equation(equation_text)
            eq = self.parse_equation(normalized_equation)
            candidate = self.parse_candidate(candidate_text)
            residual, order, zero = self._candidate_residual(eq, candidate)
        except SafeParseError as exc:
            return self._result(
                False,
                {"rule": "verify_ode_solution", "equation": equation_text},
                [],
                f"SafeParser rejected ODE/candidate: {exc}",
            )
        except Exception as exc:
            return self._result(
                False,
                {"rule": "verify_ode_solution"},
                [],
                f"ODE verification error: {type(exc).__name__}: {exc}",
            )

        steps = [
            {"step": 1, "operation": "parse_ode", "equation": str(eq)},
            {"step": 2, "operation": "parse_candidate", "candidate": str(candidate)},
            {"step": 3, "operation": "differentiate_candidate_to_order", "order": order},
            {"step": 4, "operation": "substitute_candidate", "residual": str(residual)},
        ]
        details = {
            "equation": equation_text,
            "normalized_equation": self._normalize_shorthand_equation(equation_text),
            "candidate_solution": candidate_text,
            "parsed_candidate": str(candidate),
            "order": order,
            "variable": self.variable_name,
            "dependent_function": self.function_name,
            "residual": str(residual),
            "satisfies_ode": zero is True,
            "domain": params.get("domain"),
            "assumptions": params.get("assumptions", []),
        }
        if zero is True:
            return self._result(True, details, steps)
        if zero is None:
            return self._result(
                False, details, steps,
                "Symbolic residual could not be established as zero; verification fails closed.",
                unresolved=True,
            )
        return self._result(
            False, details, steps,
            f"ODE solution residual is non-zero: {residual}",
        )

    # ---------- first-order structural families ----------

    def _first_order_parts(self, equation_text: str) -> Tuple[sp.Expr, sp.Expr, sp.Expr]:
        eq = self.parse_equation(equation_text)
        y = self.function(self.variable)
        yp = sp.diff(y, self.variable)
        # Canonical form is yp - RHS = 0. The coefficient of yp must be one.
        coeff = sp.expand(eq).coeff(yp)
        if coeff != 1:
            if coeff == 0:
                raise SafeParseError("Equation is not explicitly first-order in the dependent function.")
            eq = sp.simplify(eq / coeff)
        rhs = sp.simplify(-eq.subs(yp, 0))
        return eq, rhs, y

    def verify_separable(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        try:
            eq, rhs, y = self._first_order_parts(equation_text)
            f = self.parse_parameters(params, "f")
            g = self.parse_parameters(params, "g")
            expected = sp.simplify(f * g)
            structure = self._zero_state(rhs - expected)
            if structure is not True:
                return self._result(
                    False,
                    {"rule": "solve_separable_ode", "rhs": str(rhs), "f": str(f), "g": str(g),
                     "structure_residual": str(sp.simplify(rhs - expected))},
                    [{"step": 1, "operation": "verify_separable_factorization",
                      "expected_rhs": str(expected)}],
                    "ODE does not match dy/dx = f(x)g(y) for the supplied factors.",
                    unresolved=structure is None,
                )
            # Separation divides by g(y), so zero/equilibrium branches are
            # reported explicitly instead of silently discarded.
            equilibrium = self._zero_state(g)
            candidate = self.parse_candidate(candidate_text)
            residual, order, zero = self._candidate_residual(eq, candidate)
            relation = None
            if equilibrium is not True:
                separated_left = sp.Integral(1 / g, y)
                separated_right = sp.Integral(f, self.variable)
                relation = f"{separated_left} = {separated_right} + C"
            details = {
                "rule": "solve_separable_ode",
                "order": order,
                "f_of_x": str(f),
                "g_of_y": str(g),
                "factorization_verified": True,
                "equilibrium_factor_status": equilibrium,
                "separated_relation": relation,
                "candidate_solution": candidate_text,
                "residual": str(residual),
            }
            steps = [
                {"step": 1, "operation": "verify_rhs_factorization", "rhs": str(rhs), "f*g": str(expected)},
                {"step": 2, "operation": "separate_variables", "relation": relation},
                {"step": 3, "operation": "verify_candidate_residual", "residual": str(residual)},
            ]
            if zero is True:
                return self._result(True, details, steps)
            if zero is None:
                return self._result(False, details, steps,
                                    "Candidate residual is symbolically unresolved.", unresolved=True)
            return self._result(False, details, steps, f"Candidate residual is non-zero: {residual}")
        except SafeParseError as exc:
            return self._result(False, {"rule": "solve_separable_ode"}, [], str(exc))
        except Exception as exc:
            return self._result(False, {"rule": "solve_separable_ode"}, [],
                                f"Separable ODE error: {type(exc).__name__}: {exc}")

    def verify_linear_first_order(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        try:
            eq, rhs, y = self._first_order_parts(equation_text)
            p = self.parse_parameters(params, "P")
            q = self.parse_parameters(params, "Q")
            yp = sp.diff(y, self.variable)
            expected_eq = sp.simplify(yp + p * y - q)
            structure = self._zero_state(eq - expected_eq)
            if structure is not True:
                return self._result(
                    False,
                    {"rule": "solve_linear_first_order_ode",
                     "equation_residual": str(sp.simplify(eq - expected_eq))},
                    [{"step": 1, "operation": "verify_linear_form",
                      "expected": str(expected_eq)}],
                    "Equation is not the supplied linear first-order form y' + P(x)y = Q(x).",
                    unresolved=structure is None,
                )
            integrating_factor = sp.exp(sp.integrate(p, self.variable))
            candidate = self.parse_candidate(candidate_text)
            residual, _, zero = self._candidate_residual(eq, candidate)
            general_form = sp.Eq(
                sp.Symbol("C1", real=True),
                sp.simplify(integrating_factor * y - sp.Integral(integrating_factor * q, self.variable)),
            )
            details = {
                "rule": "solve_linear_first_order_ode",
                "P": str(p),
                "Q": str(q),
                "integrating_factor": str(integrating_factor),
                "general_solution_relation": str(general_form),
                "candidate_solution": candidate_text,
                "residual": str(residual),
            }
            steps = [
                {"step": 1, "operation": "verify_linear_form", "equation": str(expected_eq)},
                {"step": 2, "operation": "compute_integrating_factor", "value": str(integrating_factor)},
                {"step": 3, "operation": "construct_integrating_factor_relation", "relation": str(general_form)},
                {"step": 4, "operation": "verify_candidate_residual", "residual": str(residual)},
            ]
            if zero is True:
                return self._result(True, details, steps)
            if zero is None:
                return self._result(False, details, steps, "Candidate residual unresolved.", unresolved=True)
            return self._result(False, details, steps, f"Candidate residual is non-zero: {residual}")
        except SafeParseError as exc:
            return self._result(False, {"rule": "solve_linear_first_order_ode"}, [], str(exc))
        except Exception as exc:
            return self._result(False, {"rule": "solve_linear_first_order_ode"}, [],
                                f"Linear ODE error: {type(exc).__name__}: {exc}")

    def verify_bernoulli(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        try:
            n_raw = params.get("n")
            if n_raw is None:
                raise SafeParseError("edge.parameters['n'] is required")
            n = self.parse_expression(str(n_raw))
            if n in (0, 1):
                return self._result(
                    False, {"rule": "solve_bernoulli_ode", "n": str(n)},
                    [], "n=0 or n=1 is an exceptional linear case, not a Bernoulli transformation.",
                )
            p = self.parse_parameters(params, "P")
            q = self.parse_parameters(params, "Q")
            eq, rhs, y = self._first_order_parts(equation_text)
            yp = sp.diff(y, self.variable)
            expected = sp.simplify(yp + p * y - q * y**n)
            structure = self._zero_state(eq - expected)
            if structure is not True:
                return self._result(
                    False, {"rule": "solve_bernoulli_ode", "n": str(n),
                            "structure_residual": str(sp.simplify(eq - expected))},
                    [{"step": 1, "operation": "verify_bernoulli_form", "expected": str(expected)}],
                    "Equation does not match y' + P(x)y = Q(x)y^n.",
                    unresolved=structure is None,
                )
            v = sp.Symbol("v", real=True)
            transformed = sp.Eq(
                sp.diff(v, self.variable) + (1 - n) * p * v,
                (1 - n) * q,
            )
            candidate = self.parse_candidate(candidate_text)
            residual, _, zero = self._candidate_residual(eq, candidate)
            details = {
                "rule": "solve_bernoulli_ode",
                "n": str(n),
                "P": str(p),
                "Q": str(q),
                "transformation": f"v = y**({sp.simplify(1-n)})",
                "transformed_linear_equation": str(transformed),
                "candidate_solution": candidate_text,
                "residual": str(residual),
                "nonzero_y_required": True,
            }
            steps = [
                {"step": 1, "operation": "verify_bernoulli_form", "equation": str(expected)},
                {"step": 2, "operation": "transform", "substitution": f"v=y**({sp.simplify(1-n)})"},
                {"step": 3, "operation": "verify_transformed_linear_equation", "equation": str(transformed)},
                {"step": 4, "operation": "verify_candidate_residual", "residual": str(residual)},
            ]
            if zero is True:
                return self._result(True, details, steps)
            if zero is None:
                return self._result(False, details, steps, "Candidate residual unresolved.", unresolved=True)
            return self._result(False, details, steps, f"Candidate residual is non-zero: {residual}")
        except SafeParseError as exc:
            return self._result(False, {"rule": "solve_bernoulli_ode"}, [], str(exc))
        except Exception as exc:
            return self._result(False, {"rule": "solve_bernoulli_ode"}, [],
                                f"Bernoulli ODE error: {type(exc).__name__}: {exc}")

    # ---------- exact equations ----------

    def verify_exact(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        try:
            xname = str(params.get("x", "x"))
            yname = str(params.get("y", "y"))
            x = sp.Symbol(xname, real=True)
            y = sp.Symbol(yname, real=True)
            parser = SafeParser()
            loc = {xname: x, yname: y}
            if "M" not in params or "N" not in params:
                raise SafeParseError("edge.parameters['M'] and ['N'] are required")
            M = parser.parse(str(params["M"]), extra_locals=loc)
            N = parser.parse(str(params["N"]), extra_locals=loc)
            exactness = sp.simplify(sp.diff(M, y) - sp.diff(N, x))
            exact_zero = self._zero_state(exactness)
            if exact_zero is not True:
                return self._result(
                    False,
                    {"rule": "solve_exact_ode", "M": str(M), "N": str(N),
                     "exactness_residual": str(exactness)},
                    [{"step": 1, "operation": "check_exactness", "residual": str(exactness)}],
                    "The differential form is not established as exact.",
                    unresolved=exact_zero is None,
                )
            F0 = sp.integrate(M, x)
            hprime = sp.simplify(N - sp.diff(F0, y))
            h = sp.integrate(hprime, y)
            F = sp.simplify(F0 + h)
            candidate = parser.parse(str(candidate_text), extra_locals=loc)
            gx = sp.simplify(sp.diff(candidate, x) - M)
            gy = sp.simplify(sp.diff(candidate, y) - N)
            zx, zy = self._zero_state(gx), self._zero_state(gy)
            details = {
                "rule": "solve_exact_ode",
                "M": str(M),
                "N": str(N),
                "exactness_verified": True,
                "potential": str(F),
                "candidate_potential": str(candidate),
                "candidate_dx_residual": str(gx),
                "candidate_dy_residual": str(gy),
                "implicit_solution": f"{F} = C",
            }
            steps = [
                {"step": 1, "operation": "check_exactness", "residual": str(exactness)},
                {"step": 2, "operation": "integrate_M_wrt_x", "value": str(F0)},
                {"step": 3, "operation": "recover_y_only_term", "derivative": str(hprime)},
                {"step": 4, "operation": "construct_potential", "value": str(F)},
                {"step": 5, "operation": "verify_candidate_potential",
                 "dx_residual": str(gx), "dy_residual": str(gy)},
            ]
            if zx is True and zy is True:
                return self._result(True, details, steps)
            if zx is None or zy is None:
                return self._result(False, details, steps,
                                    "Candidate potential equivalence is unresolved.", unresolved=True)
            return self._result(False, details, steps, "Candidate potential does not reproduce M and N.")
        except SafeParseError as exc:
            return self._result(False, {"rule": "solve_exact_ode"}, [], str(exc))
        except Exception as exc:
            return self._result(False, {"rule": "solve_exact_ode"}, [],
                                f"Exact ODE error: {type(exc).__name__}: {exc}")

    # ---------- higher-order constant coefficients ----------

    def _constant_coefficient_data(self, equation_text: str) -> Tuple[sp.Expr, int, List[sp.Expr], sp.Expr]:
        eq = self.parse_equation(equation_text)
        y = self.function(self.variable)
        derivatives = [d for d in eq.atoms(sp.Derivative) if d.expr == y]
        order = max([len(d.variables) for d in derivatives] + [0])
        if order < 1:
            raise SafeParseError("Constant-coefficient ODE must contain at least one derivative.")
        coeffs: List[sp.Expr] = []
        for n in range(order, -1, -1):
            atom = sp.diff(y, self.variable, n) if n else y
            coeffs.append(sp.expand(eq).coeff(atom))
        # Remove the linear homogeneous part and ensure no nonlinear residual.
        linear = sum(coeffs[i] * sp.diff(y, self.variable, order-i) if order-i else coeffs[i] * y
                     for i in range(order + 1))
        nonlinear = sp.simplify(eq - linear)
        # Coefficients must be independent of the independent variable.
        if any(c.has(self.variable) for c in coeffs):
            raise SafeParseError("Coefficient depends on the independent variable.")
        return eq, order, coeffs, nonlinear

    def _root_basis(self, polynomial: sp.Expr, order: int) -> Optional[List[sp.Expr]]:
        try:
            roots = sp.roots(polynomial)
        except Exception:
            return None
        if not roots:
            return None
        basis: List[sp.Expr] = []
        for root, multiplicity in roots.items():
            real, imag = sp.expand_complex(root).as_real_imag()
            if imag == 0:
                for k in range(int(multiplicity)):
                    basis.append(self.variable**k * sp.exp(real * self.variable))
            elif imag.is_positive is True:
                for k in range(int(multiplicity)):
                    factor = self.variable**k * sp.exp(real * self.variable)
                    basis.extend([
                        factor * sp.cos(imag * self.variable),
                        factor * sp.sin(imag * self.variable),
                    ])
            elif imag.is_negative is True:
                # The conjugate root is represented by the same real basis.
                continue
            else:
                return None
        if len(basis) != order:
            return None
        return basis

    def verify_constant_coefficient(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        try:
            eq, order, coeffs, forcing = self._constant_coefficient_data(equation_text)
            if self._zero_state(forcing) is not True:
                return self._result(
                    False,
                    {"rule": "solve_constant_coefficient_ode",
                     "forcing_or_nonlinear_residual": str(forcing)},
                    [],
                    "Only homogeneous linear constant-coefficient ODEs are supported by this rule.",
                    unresolved=self._zero_state(forcing) is None,
                )
            lam = sp.Symbol("lambda")
            polynomial = sum(coeffs[i] * lam ** (order-i) for i in range(order + 1))
            candidate = self.parse_candidate(candidate_text)
            residual, _, zero = self._candidate_residual(eq, candidate)
            basis = self._root_basis(polynomial, order)
            roots = sp.roots(polynomial)
            root_info = [
                {"root": str(root), "multiplicity": int(mult)}
                for root, mult in roots.items()
            ]
            details = {
                "rule": "solve_constant_coefficient_ode",
                "order": order,
                "coefficients_high_to_low": [str(c) for c in coeffs],
                "characteristic_polynomial": str(polynomial),
                "roots": root_info,
                "homogeneous_basis": [str(b) for b in basis] if basis else None,
                "repeated_roots_present": any(int(m) > 1 for m in roots.values()),
                "complex_roots_present": any(sp.im(root).is_zero is not True for root in roots),
                "candidate_solution": candidate_text,
                "residual": str(residual),
            }
            steps = [
                {"step": 1, "operation": "extract_constant_coefficients", "coefficients": [str(c) for c in coeffs]},
                {"step": 2, "operation": "build_characteristic_polynomial", "polynomial": str(polynomial)},
                {"step": 3, "operation": "classify_characteristic_roots", "roots": root_info},
                {"step": 4, "operation": "verify_candidate_residual", "residual": str(residual)},
            ]
            if zero is True:
                return self._result(True, details, steps)
            if zero is None:
                return self._result(False, details, steps, "Candidate residual unresolved.", unresolved=True)
            return self._result(False, details, steps, f"Candidate residual is non-zero: {residual}")
        except SafeParseError as exc:
            return self._result(False, {"rule": "solve_constant_coefficient_ode"}, [], str(exc))
        except Exception as exc:
            return self._result(False, {"rule": "solve_constant_coefficient_ode"}, [],
                                f"Constant-coefficient ODE error: {type(exc).__name__}: {exc}")

    # ---------- initial / boundary conditions ----------

    def _condition_residual(
        self, condition_text: str, candidate: sp.Expr
    ) -> Tuple[sp.Expr, Optional[bool]]:
        parser = SafeParser()
        fn = self.function
        loc = self._locals()
        cond = parser.parse_equation(condition_text, extra_locals=loc)
        replacements: Dict[sp.Expr, sp.Expr] = {}
        for atom in cond.atoms(AppliedUndef):
            if atom.func == fn:
                arg = atom.args[0]
                replacements[atom] = candidate.subs(self.variable, arg)
        for atom in cond.atoms(sp.Derivative):
            if atom.expr.func == fn:
                vars_ = atom.variables
                if all(v == self.variable for v in vars_):
                    replacements[atom] = sp.diff(candidate, self.variable, len(vars_)).subs(
                        self.variable, atom.expr.args[0]
                    )
        residual = sp.simplify(cond.subs(replacements))
        return residual, self._zero_state(residual)

    def verify_ivp(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        base = self.verify_solution(equation_text, candidate_text, params)
        if not base.passed:
            return base
        conditions = params.get("initial_conditions")
        if not isinstance(conditions, list) or not conditions:
            return self._result(False, base.details, base.steps,
                                "initial_conditions must be a non-empty list.")
        candidate = self.parse_candidate(candidate_text)
        condition_results = []
        unresolved = False
        for condition in conditions:
            residual, zero = self._condition_residual(str(condition), candidate)
            condition_results.append({"condition": str(condition), "residual": str(residual), "satisfied": zero is True})
            unresolved = unresolved or zero is None
            if zero is False:
                return self._result(
                    False,
                    {**base.details, "initial_conditions": condition_results},
                    base.steps,
                    f"Initial condition failed: {condition}",
                )
        if unresolved:
            return self._result(False, {**base.details, "initial_conditions": condition_results},
                                base.steps, "Initial-condition verification unresolved.", unresolved=True)
        return self._result(True, {**base.details, "initial_conditions": condition_results},
                            base.steps + [{"step": 5, "operation": "verify_initial_conditions",
                                           "conditions": condition_results}])

    def verify_bvp(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        base = self.verify_solution(equation_text, candidate_text, params)
        if not base.passed:
            return base
        conditions = params.get("boundary_conditions")
        if not isinstance(conditions, list) or not conditions:
            return self._result(False, base.details, base.steps,
                                "boundary_conditions must be a non-empty list.")
        candidate = self.parse_candidate(candidate_text)
        results = []
        unresolved = False
        for condition in conditions:
            residual, zero = self._condition_residual(str(condition), candidate)
            results.append({"condition": str(condition), "residual": str(residual), "satisfied": zero is True})
            unresolved = unresolved or zero is None
            if zero is False:
                return self._result(False, {**base.details, "boundary_conditions": results},
                                    base.steps, f"Boundary condition failed: {condition}")
        if unresolved:
            return self._result(False, {**base.details, "boundary_conditions": results},
                                base.steps, "Boundary-condition verification unresolved.", unresolved=True)
        return self._result(True, {**base.details, "boundary_conditions": results},
                            base.steps + [{"step": 5, "operation": "verify_boundary_conditions",
                                           "conditions": results}])

    # ---------- coupled systems ----------

    def _parse_tuple(self, text: str, function_names: Sequence[str]) -> Tuple[sp.Expr, ...]:
        expr = self.parse_expression(text, function_names)
        if not isinstance(expr, sp.Tuple):
            raise SafeParseError("ODE system representation must be a tuple of equations/expressions.")
        return tuple(expr.args)

    def verify_system(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        functions = params.get("functions")
        if not isinstance(functions, list) or not functions:
            raise SafeParseError("edge.parameters['functions'] must be a non-empty list")
        if not all(isinstance(n, str) and n for n in functions):
            raise SafeParseError("ODE system function names must be non-empty strings")
        eqs = self._parse_tuple(equation_text, functions)
        candidates = self._parse_tuple(candidate_text, functions)
        if len(eqs) != len(candidates) or len(eqs) != len(functions):
            raise SafeParseError("System equation, candidate, and function counts must agree.")
        fn_objs = {name: sp.Function(name)(self.variable) for name in functions}
        residuals = []
        unresolved = False
        for eq, candidate in zip(eqs, candidates):
            # Each system equation should be expressed as an equality residual.
            replacements: Dict[sp.Expr, sp.Expr] = {}
            for name, fn in fn_objs.items():
                replacements[fn] = candidate if name == functions[0] else fn
            # Build all candidate expressions by positional function name.
            all_candidates = dict(zip(fn_objs.values(), candidates))
            residual = eq.subs(all_candidates)
            for d in list(residual.atoms(sp.Derivative)):
                if d.expr in all_candidates and all(v == self.variable for v in d.variables):
                    residual = residual.subs(d, sp.diff(all_candidates[d.expr], self.variable, len(d.variables)))
            residual = sp.simplify(residual)
            z = self._zero_state(residual)
            residuals.append(str(residual))
            if z is False:
                return self._result(False, {"rule": "verify_ode_system", "residuals": residuals},
                                    [], f"System equation residual is non-zero: {residual}")
            if z is None:
                unresolved = True
        details = {
            "rule": "verify_ode_system",
            "functions": functions,
            "equation_count": len(eqs),
            "candidate_count": len(candidates),
            "residuals": residuals,
        }
        steps = [{"step": 1, "operation": "substitute_system_solution", "residuals": residuals}]
        if unresolved:
            return self._result(False, details, steps, "One or more system residuals are unresolved.", unresolved=True)
        return self._result(True, details, steps)

    # ---------- phase-space conversion ----------

    def phase_space(
        self, equation_text: str, candidate_text: str, params: Dict[str, Any]
    ) -> ODEResult:
        eq = self.parse_equation(equation_text)
        y = self.function(self.variable)
        derivatives = [d for d in eq.atoms(sp.Derivative) if d.expr == y]
        order = max([len(d.variables) for d in derivatives] + [0])
        if order < 2:
            raise SafeParseError("Phase-space conversion requires order >= 2.")
        highest = sp.diff(y, self.variable, order)
        solutions = sp.solve(sp.Eq(eq, 0), highest, dict=True)
        if len(solutions) != 1 or highest not in solutions[0]:
            return self._result(
                False,
                {"rule": "ode_phase_space", "order": order},
                [],
                "Highest derivative could not be isolated uniquely.",
                unresolved=True,
            )
        highest_rhs = sp.simplify(solutions[0][highest])
        state_names = params.get("state_variables") or [f"z{i}" for i in range(order)]
        if not isinstance(state_names, list) or len(state_names) != order:
            raise SafeParseError("state_variables must contain exactly one name per derivative state.")
        states = [sp.Symbol(str(name)) for name in state_names]
        substitution = {sp.diff(y, self.variable, i): states[i] for i in range(order)}
        expected = [states[i + 1] for i in range(order - 1)] + [sp.simplify(highest_rhs.subs(substitution))]
        candidate = self._parse_tuple(candidate_text, [])
        if len(candidate) != order:
            raise SafeParseError("Phase-space candidate must be a tuple with one RHS per state.")
        diffs = [sp.simplify(a-b) for a,b in zip(candidate, expected)]
        checks = [self._zero_state(d) for d in diffs]
        details = {
            "rule": "ode_phase_space",
            "order": order,
            "state_variables": state_names,
            "expected_rhs": [str(v) for v in expected],
            "candidate_rhs": [str(v) for v in candidate],
            "differences": [str(v) for v in diffs],
            "equivalence": checks,
        }
        steps = [
            {"step": 1, "operation": "isolate_highest_derivative", "rhs": str(highest_rhs)},
            {"step": 2, "operation": "construct_first_order_state_system", "rhs": [str(v) for v in expected]},
            {"step": 3, "operation": "verify_phase_space_candidate", "differences": [str(v) for v in diffs]},
        ]
        if all(c is True for c in checks):
            return self._result(True, details, steps)
        if any(c is None for c in checks):
            return self._result(False, details, steps, "Phase-space equivalence unresolved.", unresolved=True)
        return self._result(False, details, steps, "Phase-space representation does not match the ODE.")

