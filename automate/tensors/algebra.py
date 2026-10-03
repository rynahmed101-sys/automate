"""
Symbolic Tensor Algebra Engine for Automate.

Computes component-level geometric tensors for Riemannian and pseudo-Riemannian manifolds:
  - Christoffel symbols (second kind): Γ^σ_{μν}
  - Riemann curvature tensor: R^σ_{ρμν}
  - Ricci tensor: R_{μν} = R^σ_{μσν}
  - Ricci scalar: R = g^{μν} R_{μν}
  - Einstein tensor: G_{μν} = R_{μν} - (1/2) g_{μν} R
  - Geodesic equations: d²x^σ/dτ² + Γ^σ_{μν} (dx^μ/dτ)(dx^ν/dτ) = 0
  - Bianchi identity verification: ∇^μ G_{μν} = 0 (contracted)

All computations are fully symbolic (SymPy). No hardcoded metric. The user provides
a metric tensor as a sympy.Matrix and a list of coordinate symbols.

Usage example (2D sphere):
    coords = sp.symbols('theta phi', real=True)
    g = sp.Matrix([
        [r**2,                  0],
        [0,     r**2 * sp.sin(theta)**2],
    ])
    tg = TensorGeometry(g, [theta, phi])
    christoffel = tg.christoffel_symbols()
    riemann = tg.riemann_tensor()
    ricci = tg.ricci_tensor()
    R = tg.ricci_scalar()
    G = tg.einstein_tensor()
    geodesic = tg.geodesic_equations()
"""

from typing import Dict, Any, List, Optional, Tuple
import sympy as sp


class TensorGeometry:
    """
    Symbolic Riemannian/pseudo-Riemannian tensor algebra.

    Parameters
    ----------
    metric : sp.Matrix
        Covariant metric tensor g_{μν}, shape (n, n), components as SymPy expressions.
    coordinates : list of sp.Symbol
        Coordinate symbols [x^0, x^1, ..., x^(n-1)].
    affine_parameter : sp.Symbol, optional
        Affine parameter (default: τ). Used for geodesic equations.
    simplify : bool
        Whether to call sp.simplify() on each computed component.
        Set False for large metrics to avoid timeouts; use trigsimp, etc. instead.
    """

    def __init__(
        self,
        metric: sp.Matrix,
        coordinates: List[sp.Symbol],
        affine_parameter: Optional[sp.Symbol] = None,
        simplify: bool = True,
    ):
        n = len(coordinates)
        if metric.shape != (n, n):
            raise ValueError(
                f"Metric shape {metric.shape} does not match "
                f"number of coordinates ({n}). Expected ({n}, {n})."
            )
        self.g = metric
        self.coords = list(coordinates)
        self.n = n
        self.tau = affine_parameter or sp.Symbol("tau", real=True)
        self._simplify = simplify

        # Compute inverse metric once
        self.g_inv = metric.inv()

        # Cached results
        self._christoffel: Optional[Dict[Tuple[int, int, int], sp.Expr]] = None
        self._riemann: Optional[Dict[Tuple[int, int, int, int], sp.Expr]] = None
        self._ricci: Optional[sp.Matrix] = None
        self._ricci_scalar: Optional[sp.Expr] = None
        self._einstein: Optional[sp.Matrix] = None

    def _s(self, expr: sp.Expr) -> sp.Expr:
        """Optionally simplify expression."""
        if self._simplify:
            return sp.simplify(expr)
        return expr

    # ------------------------------------------------------------------
    # Christoffel symbols Γ^σ_{μν}
    # ------------------------------------------------------------------
    def christoffel_symbols(self) -> Dict[Tuple[int, int, int], sp.Expr]:
        """
        Returns a dict {(sigma, mu, nu): Γ^σ_{μν}} for all index triples.

        Γ^σ_{μν} = 1/2 g^{σρ} (∂_ν g_{ρμ} + ∂_μ g_{ρν} - ∂_ρ g_{μν})
        """
        if self._christoffel is not None:
            return self._christoffel

        g = self.g
        g_inv = self.g_inv
        x = self.coords
        n = self.n

        result: Dict[Tuple[int, int, int], sp.Expr] = {}

        for sigma in range(n):
            for mu in range(n):
                for nu in range(n):
                    val = sp.Integer(0)
                    for rho in range(n):
                        val += g_inv[sigma, rho] * (
                            sp.diff(g[rho, mu], x[nu])
                            + sp.diff(g[rho, nu], x[mu])
                            - sp.diff(g[mu, nu], x[rho])
                        )
                    result[(sigma, mu, nu)] = self._s(val / 2)

        self._christoffel = result
        return result

    # ------------------------------------------------------------------
    # Riemann curvature tensor R^σ_{ρμν}
    # ------------------------------------------------------------------
    def riemann_tensor(self) -> Dict[Tuple[int, int, int, int], sp.Expr]:
        """
        Returns a dict {(sigma, rho, mu, nu): R^σ_{ρμν}}.

        R^σ_{ρμν} = ∂_μ Γ^σ_{νρ} - ∂_ν Γ^σ_{μρ}
                   + Γ^σ_{μλ} Γ^λ_{νρ} - Γ^σ_{νλ} Γ^λ_{μρ}
        """
        if self._riemann is not None:
            return self._riemann

        Gamma = self.christoffel_symbols()
        x = self.coords
        n = self.n

        result: Dict[Tuple[int, int, int, int], sp.Expr] = {}

        for sigma in range(n):
            for rho in range(n):
                for mu in range(n):
                    for nu in range(n):
                        # Derivative terms
                        val = (
                            sp.diff(Gamma[(sigma, nu, rho)], x[mu])
                            - sp.diff(Gamma[(sigma, mu, rho)], x[nu])
                        )
                        # Quadratic terms
                        for lam in range(n):
                            val += (
                                Gamma[(sigma, mu, lam)] * Gamma[(lam, nu, rho)]
                                - Gamma[(sigma, nu, lam)] * Gamma[(lam, mu, rho)]
                            )
                        result[(sigma, rho, mu, nu)] = self._s(val)

        self._riemann = result
        return result

    # ------------------------------------------------------------------
    # Ricci tensor R_{μν} = R^σ_{μσν}
    # ------------------------------------------------------------------
    def ricci_tensor(self) -> sp.Matrix:
        """
        Returns the Ricci tensor as an n×n SymPy Matrix.
        R_{μν} = R^σ_{μσν}  (trace over first and third index of Riemann)
        """
        if self._ricci is not None:
            return self._ricci

        Riemann = self.riemann_tensor()
        n = self.n
        R_munu = sp.zeros(n, n)

        for mu in range(n):
            for nu in range(n):
                val = sp.Integer(0)
                for sigma in range(n):
                    val += Riemann[(sigma, mu, sigma, nu)]
                R_munu[mu, nu] = self._s(val)

        self._ricci = R_munu
        return R_munu

    # ------------------------------------------------------------------
    # Ricci scalar R = g^{μν} R_{μν}
    # ------------------------------------------------------------------
    def ricci_scalar(self) -> sp.Expr:
        """
        Returns the Ricci scalar R = g^{μν} R_{μν}.
        """
        if self._ricci_scalar is not None:
            return self._ricci_scalar

        Ricci = self.ricci_tensor()
        g_inv = self.g_inv
        n = self.n

        R = sp.Integer(0)
        for mu in range(n):
            for nu in range(n):
                R += g_inv[mu, nu] * Ricci[mu, nu]

        self._ricci_scalar = self._s(R)
        return self._ricci_scalar

    # ------------------------------------------------------------------
    # Einstein tensor G_{μν} = R_{μν} - (1/2) g_{μν} R
    # ------------------------------------------------------------------
    def einstein_tensor(self) -> sp.Matrix:
        """
        Returns the Einstein tensor G_{μν} = R_{μν} - (1/2) g_{μν} R.
        """
        if self._einstein is not None:
            return self._einstein

        Ricci = self.ricci_tensor()
        R_scalar = self.ricci_scalar()
        g = self.g
        n = self.n

        G = sp.zeros(n, n)
        for mu in range(n):
            for nu in range(n):
                G[mu, nu] = self._s(Ricci[mu, nu] - sp.Rational(1, 2) * g[mu, nu] * R_scalar)

        self._einstein = G
        return G

    # ------------------------------------------------------------------
    # Geodesic equations d²x^σ/dτ² + Γ^σ_{μν} (dx^μ/dτ)(dx^ν/dτ) = 0
    # ------------------------------------------------------------------
    def geodesic_equations(self) -> List[sp.Expr]:
        """
        Returns list of n geodesic equation LHS expressions (equated to 0):
          d²x^σ/dτ² + Γ^σ_{μν} (dx^μ/dτ)(dx^ν/dτ)  for σ = 0, ..., n-1.

        Coordinates are treated as functions of the affine parameter τ.
        """
        Gamma = self.christoffel_symbols()
        tau = self.tau
        n = self.n

        # x^σ(τ) and their first/second derivatives
        x_tau = [sp.Function(str(q))(tau) for q in self.coords]
        x_dot = [sp.diff(xf, tau) for xf in x_tau]
        x_ddot = [sp.diff(xf, tau, 2) for xf in x_tau]

        # Gamma substitution: replace bare symbols with x(tau)
        coord_subs = {self.coords[i]: x_tau[i] for i in range(n)}

        eqs = []
        for sigma in range(n):
            expr = x_ddot[sigma]
            for mu in range(n):
                for nu in range(n):
                    G_sigma_munu = Gamma[(sigma, mu, nu)].subs(coord_subs)
                    expr = expr + G_sigma_munu * x_dot[mu] * x_dot[nu]
            eqs.append(self._s(expr))

        return eqs

    # ------------------------------------------------------------------
    # Bianchi identity verification: ∇^μ G_{μν} = 0
    # ------------------------------------------------------------------
    def verify_contracted_bianchi_identity(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifies the contracted Bianchi identity ∇^μ G_{μν} = 0.

        Computes ∂_μ G^μ_ν + Γ^μ_{μλ} G^λ_ν - Γ^λ_{μν} G^μ_λ
        and checks each component is zero.

        Returns (passed, details_dict).
        """
        G_lower = self.einstein_tensor()
        g_inv = self.g_inv
        Gamma = self.christoffel_symbols()
        x = self.coords
        n = self.n

        # Raise first index: G^μ_ν = g^{μρ} G_{ρν}
        G_mixed = sp.zeros(n, n)
        for mu in range(n):
            for nu in range(n):
                val = sp.Integer(0)
                for rho in range(n):
                    val += g_inv[mu, rho] * G_lower[rho, nu]
                G_mixed[mu, nu] = self._s(val)

        divergences = []
        all_zero = True
        for nu in range(n):
            div_nu = sp.Integer(0)
            for mu in range(n):
                # ∂_μ G^μ_ν
                div_nu += sp.diff(G_mixed[mu, nu], x[mu])
                for lam in range(n):
                    # + Γ^μ_{μλ} G^λ_ν
                    div_nu += Gamma[(mu, mu, lam)] * G_mixed[lam, nu]
                    # - Γ^λ_{μν} G^μ_λ
                    div_nu -= Gamma[(lam, mu, nu)] * G_mixed[mu, lam]

            div_nu_simplified = self._s(div_nu)
            is_zero = (div_nu_simplified == 0)
            if not is_zero:
                all_zero = False
            divergences.append({
                "nu": nu,
                "coord": str(self.coords[nu]),
                "divergence": str(div_nu_simplified),
                "is_zero": is_zero
            })

        return all_zero, {
            "bianchi_components": divergences,
            "all_zero": all_zero
        }

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Returns a summary of all computed tensor quantities."""
        Gamma = self.christoffel_symbols()
        Riemann = self.riemann_tensor()
        Ricci = self.ricci_tensor()
        R = self.ricci_scalar()
        G = self.einstein_tensor()

        # Count non-zero Christoffel symbols
        nonzero_christoffel = sum(1 for v in Gamma.values() if v != 0)
        nonzero_riemann = sum(1 for v in Riemann.values() if v != 0)

        return {
            "dimension": self.n,
            "coordinates": [str(c) for c in self.coords],
            "christoffel_nonzero": nonzero_christoffel,
            "riemann_nonzero": nonzero_riemann,
            "ricci_tensor": [[str(Ricci[i, j]) for j in range(self.n)] for i in range(self.n)],
            "ricci_scalar": str(R),
            "einstein_tensor": [[str(G[i, j]) for j in range(self.n)] for i in range(self.n)],
        }
