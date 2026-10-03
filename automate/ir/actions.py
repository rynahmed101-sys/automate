"""
Field-Theory Actions, Differential Geometry Primitives, and Functional Calculus for Automate IR.
Provides first-class representations for:
- Action functionals: S[phi] = int d^4x sqrt(-g) L
- Lagrangian densities, integration measures, boundary terms
- Differential geometry: Metric, Christoffel symbols, Riemann, Ricci, Einstein tensor
- Functional variations: delta S / delta phi = 0
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from automate.ir.tensors import TensorIndex, TensorQuantity


class Manifold(BaseModel):
    """
    Smooth differentiable manifold with dimension and metric signature.
    """
    name: str = Field(default="M", description="Manifold identifier")
    dimension: int = Field(default=4, description="Manifold topological dimension")
    signature: str = Field(default="(-,+,+,+)", description="Metric signature: Lorentzian or Riemannian")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CoordinateChart(BaseModel):
    """
    Local coordinate chart on a manifold.
    """
    name: str = Field(default="standard", description="Chart name")
    coordinates: List[str] = Field(default_factory=lambda: ["t", "x", "y", "z"])
    domain: str = Field(default="R^4", description="Coordinate patch domain")


class MetricTensor(BaseModel):
    """
    Metric tensor g_{mu nu} or inverse metric g^{mu nu}.
    """
    name: str = Field(default="g", description="Metric symbol")
    indices: List[TensorIndex] = Field(
        default_factory=lambda: [
            TensorIndex(symbol="mu", position="lower"),
            TensorIndex(symbol="nu", position="lower")
        ]
    )
    is_inverse: bool = Field(default=False, description="True for g^{mu nu}")
    dimension: str = Field(default="dimensionless", description="Physical dimension")
    symmetry: str = Field(default="symmetric", description="g_{mu nu} = g_{nu mu}")


class ChristoffelSymbols(BaseModel):
    """
    Levi-Civita connection coefficients Gamma^rho_{mu nu}.
    Symmetric in lower indices: Gamma^rho_{mu nu} = Gamma^rho_{nu mu}.
    """
    name: str = Field(default="Gamma")
    upper_index: TensorIndex = Field(default_factory=lambda: TensorIndex(symbol="rho", position="upper"))
    lower_indices: List[TensorIndex] = Field(
        default_factory=lambda: [
            TensorIndex(symbol="mu", position="lower"),
            TensorIndex(symbol="nu", position="lower")
        ]
    )
    symmetric_lower: bool = True
    metric_symbol: str = "g"


class RiemannTensor(BaseModel):
    """
    Riemann curvature tensor R^rho_{sigma mu nu} (rank 4).
    """
    name: str = Field(default="R")
    indices: List[TensorIndex] = Field(
        default_factory=lambda: [
            TensorIndex(symbol="rho", position="upper"),
            TensorIndex(symbol="sigma", position="lower"),
            TensorIndex(symbol="mu", position="lower"),
            TensorIndex(symbol="nu", position="lower")
        ]
    )
    antisymmetric_pair: bool = Field(default=True, description="Antisymmetric in mu, nu")


class RicciTensor(BaseModel):
    """
    Ricci curvature tensor R_{mu nu} = R^rho_{mu rho nu} (rank 2 symmetric).
    """
    name: str = Field(default="R")
    indices: List[TensorIndex] = Field(
        default_factory=lambda: [
            TensorIndex(symbol="mu", position="lower"),
            TensorIndex(symbol="nu", position="lower")
        ]
    )
    is_symmetric: bool = True
    dimension: str = "L^-2"


class RicciScalar(BaseModel):
    """
    Ricci curvature scalar R = g^{mu nu} R_{mu nu} (rank 0 scalar).
    """
    name: str = Field(default="R")
    dimension: str = Field(default="L^-2", description="Curvature dimension: 1/length^2")
    rank: int = 0


class EinsteinTensor(BaseModel):
    """
    Einstein tensor G_{mu nu} = R_{mu nu} - 1/2 R g_{mu nu}.
    Divergence-free by Bianchi identity: nabla^mu G_{mu nu} = 0.
    """
    name: str = Field(default="G")
    indices: List[TensorIndex] = Field(
        default_factory=lambda: [
            TensorIndex(symbol="mu", position="lower"),
            TensorIndex(symbol="nu", position="lower")
        ]
    )
    is_symmetric: bool = True
    dimension: str = "L^-2"


class IntegrationMeasure(BaseModel):
    """
    Invariant spacetime integration measure, e.g. d^4x sqrt(-g).
    """
    coordinates: List[str] = Field(default_factory=lambda: ["x^0", "x^1", "x^2", "x^3"])
    volume_form: str = Field(default="d^4x", description="Differential coordinate volume")
    metric_determinant_factor: str = Field(default="sqrt(-g)", description="Volume determinant prefactor")
    dimension: str = Field(default="L^4", description="Measure dimension")


class LagrangianDensity(BaseModel):
    """
    Lagrangian density L(phi, partial_mu phi, g_{mu nu}).
    """
    name: str = Field(default="L", description="Symbolic name")
    fields: List[str] = Field(default_factory=list, description="Dynamical fields, e.g. ['g', 'phi', 'A']")
    kinetic_term: Optional[str] = None
    potential_term: Optional[str] = None
    interaction_terms: List[str] = Field(default_factory=list)
    dimension: str = Field(default="M*L^-1*T^-2", description="Energy density dimension")


class ActionFunctional(BaseModel):
    """
    Spacetime Action functional: S = prefactor * integral d^n x sqrt(-g) (L_geom + L_matter).
    """
    name: str = Field(default="S", description="Action symbol")
    prefactor: Optional[str] = Field(default=None, description="Coupling prefactor, e.g. '1 / (16 * pi * G)'")
    lagrangian_density: LagrangianDensity = Field(default_factory=LagrangianDensity)
    measure: IntegrationMeasure = Field(default_factory=IntegrationMeasure)
    boundary_terms: List[str] = Field(default_factory=list, description="e.g. Gibbons-Hawking-York boundary term")
    assumptions: List[str] = Field(default_factory=list, description="Vanishing boundary variations, asymptotia")
    dimension: str = Field(default="M*L^2*T^-1", description="Action dimension: Joule * seconds")


class FunctionalDerivative(BaseModel):
    """
    Functional derivative delta S / delta phi.
    """
    action_name: str = Field(default="S")
    target_field: str = Field(..., description="Field varied, e.g. 'g_{mu nu}' or 'phi'")
    vanishing_boundary_assumptions: List[str] = Field(default_factory=list)
    result_expression: Optional[str] = None


class FieldEquation(BaseModel):
    """
    Euler-Lagrange field equation: delta S / delta phi_a = 0.
    """
    name: str = Field(..., description="Equation name, e.g. 'EinsteinFieldEquations', 'KleinGordonEquation'")
    action: str = Field(default="S")
    field: str = Field(..., description="Dynamical field varied")
    lhs_expression: str = Field(..., description="LHS of field equation")
    rhs_expression: str = Field(default="0", description="RHS of field equation")
    free_indices: List[TensorIndex] = Field(default_factory=list)
    is_euler_lagrange: bool = True
