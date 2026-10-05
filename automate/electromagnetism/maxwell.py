"""Symbolic Maxwell, Lorentz-force, and Poynting-theorem verification.

The verifier uses the existing SafeParser and explicit Cartesian component
representations. It is intentionally conservative: vector inputs must contain
exactly three comma-separated components and unresolved symbolic identities are
reported as residuals rather than guessed away.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import sympy as sp

from automate.ir.safe_parser import SafeParser
from automate.electromagnetism.representation import ElectromagneticSystem


class MaxwellVerifier:
    """Verify the four Maxwell equations in a homogeneous isotropic SI medium."""

    def __init__(self, system: ElectromagneticSystem):
        self.system = system
        names = system.field.independent_variables
        if len(names) < 4:
            raise ValueError("Maxwell verification requires at least t, x, y, z variables.")
        self.t, self.x, self.y, self.z = [sp.Symbol(n, real=True) for n in names[:4]]
        self._locals = {str(v): v for v in (self.t, self.x, self.y, self.z)}

    def _parse_scalar(self, expression: str) -> sp.Expr:
        return SafeParser(extra_symbols=self._locals).parse(expression)

    def _parse_vector(self, expression: str, label: str) -> sp.Matrix:
        parts = [p.strip() for p in expression.split(",")]
        if len(parts) == 1 and parts[0] in {"0", "0.0"}:
            return sp.Matrix([0, 0, 0])
        if len(parts) != 3:
            raise ValueError(f"{label} must contain exactly three comma-separated components.")
        return sp.Matrix([self._parse_scalar(p) for p in parts])

    def _fields(self) -> Tuple[sp.Matrix, sp.Matrix]:
        return (
            self._parse_vector(self.system.field.electric, "Electric field"),
            self._parse_vector(self.system.field.magnetic, "Magnetic field"),
        )

    def _source(self) -> Tuple[sp.Expr, sp.Matrix]:
        rho = self._parse_scalar(self.system.source.charge_density)
        current = self._parse_vector(self.system.source.current_density, "Current density")
        return rho, current

    @staticmethod
    def _div(v: sp.Matrix, x: sp.Symbol, y: sp.Symbol, z: sp.Symbol) -> sp.Expr:
        return sp.diff(v[0], x) + sp.diff(v[1], y) + sp.diff(v[2], z)

    @staticmethod
    def _curl(v: sp.Matrix, x: sp.Symbol, y: sp.Symbol, z: sp.Symbol) -> sp.Matrix:
        return sp.Matrix([
            sp.diff(v[2], y) - sp.diff(v[1], z),
            sp.diff(v[0], z) - sp.diff(v[2], x),
            sp.diff(v[1], x) - sp.diff(v[0], y),
        ])

    def residuals(self) -> Dict[str, Any]:
        """Return the four Maxwell residuals in SI form."""
        E, B = self._fields()
        rho, J = self._source()
        eps = self._parse_scalar(self.system.constitutive.permittivity)
        mu = self._parse_scalar(self.system.constitutive.permeability)

        residuals = {
            "gauss_electric": sp.simplify(self._div(E, self.x, self.y, self.z) - rho / eps),
            "gauss_magnetic": sp.simplify(self._div(B, self.x, self.y, self.z)),
            "faraday": sp.simplify(
                self._curl(E, self.x, self.y, self.z) + B.applyfunc(lambda q: sp.diff(q, self.t))
            ),
            "ampere_maxwell": sp.simplify(
                self._curl(B, self.x, self.y, self.z)
                - mu * J
                - mu * eps * E.applyfunc(lambda q: sp.diff(q, self.t))
            ),
        }
        return {k: [str(v) for v in value] if isinstance(value, sp.MatrixBase) else str(value)
                for k, value in residuals.items()}

    def verify(self) -> Tuple[bool, Dict[str, Any], str | None]:
        residuals = self.residuals()
        zero = all(
            (all(sp.sympify(v) == 0 for v in value) if isinstance(value, list) else sp.sympify(value) == 0)
            for value in residuals.values()
        )
        return zero, {"residuals": residuals, "homogeneous_medium": True}, None if zero else "Maxwell residuals are nonzero."


class LorentzForceCalculator:
    """Construct the Lorentz force q(E + v x B) from explicit field components."""

    def __init__(self, system: ElectromagneticSystem):
        self.system = system

    def force(self, charge: str, velocity: str) -> sp.Matrix:
        verifier = MaxwellVerifier(self.system)
        q = verifier._parse_scalar(charge)
        v = verifier._parse_vector(velocity, "Velocity")
        E, B = verifier._fields()
        return sp.simplify(q * (E + v.cross(B)))


class PoyntingVerifier:
    """Verify the electromagnetic energy-balance residual in a homogeneous medium."""

    def __init__(self, system: ElectromagneticSystem):
        self.system = system

    def residual(self) -> sp.Expr:
        verifier = MaxwellVerifier(self.system)
        E, B = verifier._fields()
        _, J = verifier._source()
        eps = verifier._parse_scalar(self.system.constitutive.permittivity)
        mu = verifier._parse_scalar(self.system.constitutive.permeability)
        H = B / mu
        u = sp.simplify(eps * E.dot(E) / 2 + B.dot(H) / 2)
        S = E.cross(H)
        return sp.simplify(
            sp.diff(u, verifier.t)
            + verifier._div(S, verifier.x, verifier.y, verifier.z)
            + J.dot(E)
        )

    def verify(self) -> Tuple[bool, Dict[str, str], str | None]:
        residual = self.residual()
        passed = residual == 0
        return passed, {"poynting_residual": str(residual)}, None if passed else "Poynting-theorem residual is nonzero."
