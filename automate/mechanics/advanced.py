"""Advanced classical-mechanics verification built on the existing Lagrangian engine.

The helpers here add constraint multipliers and Hamilton-equation verification
without duplicating the established Euler-Lagrange derivation.
"""

from __future__ import annotations

from typing import Any, Dict, List
import sympy as sp

from automate.mechanics.lagrangian import LagrangianSystem
from automate.mechanics.representation import MechanicalSystemRepresentation


class ConstraintMechanicsVerifier:
    """Verify holonomic constrained Euler-Lagrange equations with multipliers."""

    def __init__(self, system: MechanicalSystemRepresentation):
        self.system = system

    def augmented_lagrangian(self) -> tuple[sp.Expr, Dict[str, sp.Symbol]]:
        """Return L + sum(lambda_a f_a) for holonomic f_a=0 constraints."""
        bad = [c.kind for c in self.system.constraints if c.kind != "holonomic"]
        if bad:
            raise ValueError(
                "Lagrange-multiplier verification currently supports only "
                "holonomic constraints."
            )
        base = self.system.as_lagrangian_system()
        L_alg = base.to_algebraic(base.lagrangian)
        multipliers = {
            f"lambda_{i}": sp.Symbol(f"lambda_{i}", real=True)
            for i, _ in enumerate(self.system.constraints, start=1)
        }
        augmented = L_alg
        for i, constraint in enumerate(self.system.constraints, start=1):
            residual = base.to_algebraic(self.system.parse(constraint.expression))
            augmented += multipliers[f"lambda_{i}"] * residual
        return sp.simplify(augmented), multipliers

    def equations(self) -> Dict[str, Any]:
        """Return constrained coordinate equations and explicit constraint equations."""
        base = self.system.as_lagrangian_system()
        augmented, multipliers = self.augmented_lagrangian()
        equations: Dict[str, Any] = {}
        for q in base.coord_names:
            dL_dv = sp.diff(augmented, base.v_syms[q])
            ddt = 0
            for coord in base.coord_names:
                ddt += sp.diff(dL_dv, base.q_syms[coord]) * base.v_syms[coord]
                ddt += sp.diff(dL_dv, base.v_syms[coord]) * base.a_syms[coord]
            ddt += sp.diff(dL_dv, base.time_sym)
            dL_dq = sp.diff(augmented, base.q_syms[q])
            equations[q] = sp.simplify(ddt - dL_dq)
        equations["constraints"] = {
            c.expression: sp.simplify(self.system.parse(c.expression))
            for c in self.system.constraints
        }
        equations["multipliers"] = {name: str(symbol) for name, symbol in multipliers.items()}
        return equations

    def verify(self, candidate_eoms: Dict[str, str]) -> tuple[bool, Dict[str, Any], str | None]:
        """Verify candidate constrained coordinate equations against the derived residuals."""
        derived = self.equations()
        base = self.system.as_lagrangian_system()
        details: Dict[str, Any] = {"derived": {}, "candidate": {}, "residuals": {}}
        passed = True
        for q in base.coord_names:
            if q not in candidate_eoms:
                return False, details, f"Missing candidate constrained equation for '{q}'."
            candidate = base._parse_equation_lhs(candidate_eoms[q])
            expected = base.to_time_dependent(derived[q])
            diff = sp.simplify(expected - candidate)
            details["derived"][q] = str(expected)
            details["candidate"][q] = str(candidate)
            details["residuals"][q] = str(diff)
            if diff != 0:
                passed = False
        return passed, details, None if passed else "Constrained Euler-Lagrange residual mismatch."


class HamiltonEquationVerifier:
    """Verify both canonical Hamilton equations for a regular Lagrangian."""

    def __init__(self, system: LagrangianSystem):
        self.system = system

    def verify(self) -> tuple[bool, Dict[str, Any], str | None]:
        H, p_syms = self.system.hamiltonian()
        L_alg = self.system.to_algebraic(self.system.lagrangian)
        momenta = {
            q: sp.diff(L_alg, self.system.v_syms[q]) for q in self.system.coord_names
        }
        p_eqs = [
            sp.Eq(p_syms[q], momenta[q]) for q in self.system.coord_names
        ]
        velocities = sp.solve(
            p_eqs,
            [self.system.v_syms[q] for q in self.system.coord_names],
            dict=True,
        )
        if not velocities:
            raise ValueError("Legendre transform is singular.")
        velocity_subs = velocities[0]

        details: Dict[str, Any] = {
            "hamiltonian": str(H),
            "coordinates": {},
        }
        passed = True

        for q in self.system.coord_names:
            expected_qdot = sp.simplify(velocity_subs[self.system.v_syms[q]])
            actual_qdot = sp.simplify(sp.diff(H, p_syms[q]))
            q_residual = sp.simplify(actual_qdot - expected_qdot)

            # Along Euler-Lagrange solutions, dp_i/dt = dL/dq_i.
            expected_pdot = sp.simplify(
                sp.diff(L_alg, self.system.q_syms[q]).subs(velocity_subs)
            )
            actual_pdot = sp.simplify(-sp.diff(H, self.system.q_syms[q]))
            p_residual = sp.simplify(actual_pdot - expected_pdot)

            details["coordinates"][q] = {
                "qdot_residual": str(q_residual),
                "pdot_residual": str(p_residual),
                "expected_qdot": str(expected_qdot),
                "actual_qdot": str(actual_qdot),
                "expected_pdot": str(expected_pdot),
                "actual_pdot": str(actual_pdot),
            }
            if q_residual != 0 or p_residual != 0:
                passed = False

        return passed, details, None if passed else "Hamilton-equation residual mismatch."
