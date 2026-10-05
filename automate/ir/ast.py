"""
Canonical Intermediate Representation (IR) AST for mathematical physics.
Supports scalars, vectors, matrices, tensors, derivatives, integrals,
differential equations, physical constants, dimensions, statistical models,
and observables.
"""

from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from automate.ir.dimensions import Dimension


class PhysicalConstant(BaseModel):
    name: str = Field(..., description="Symbolic name, e.g. c, hbar, G")
    symbol: str = Field(..., description="Unicode/LaTeX symbol")
    value: float = Field(..., description="Numerical value in SI units")
    uncertainty: float = Field(default=0.0, description="Standard uncertainty")
    dimension: str = Field(default="", description="Physical dimension string")
    unit: str = Field(default="", description="SI unit label, e.g. m/s, J*s")
    description: str = Field(default="")


class SymbolNode(BaseModel):
    kind: Literal["symbol"] = "symbol"
    name: str
    dimension: str = ""
    domain: Literal["real", "positive_real", "complex", "integer"] = "real"
    latex: Optional[str] = None


class NumberNode(BaseModel):
    kind: Literal["number"] = "number"
    value: Union[int, float]
    dimension: str = ""


class BinaryOpNode(BaseModel):
    kind: Literal["binary_op"] = "binary_op"
    op: Literal["add", "sub", "mul", "div", "pow"]
    left: Dict[str, Any]
    right: Dict[str, Any]


class UnaryOpNode(BaseModel):
    kind: Literal["unary_op"] = "unary_op"
    op: Literal["neg", "sin", "cos", "tan", "exp", "log", "sqrt", "abs"]
    operand: Dict[str, Any]


class DerivativeNode(BaseModel):
    kind: Literal["derivative"] = "derivative"
    target: Dict[str, Any]
    wrt: List[str]  # e.g. ["t"] or ["t", "t"] for 2nd order
    deriv_type: Literal["total", "partial", "time_dot", "covariant", "functional", "directional"] = "total"
    order: int = 1
    connection_symbol: Optional[str] = None  # for covariant derivative, e.g. 'Gamma'
    direction_vector: Optional[str] = None  # for directional derivative


class IntegralNode(BaseModel):
    kind: Literal["integral"] = "integral"
    integrand: Dict[str, Any]
    variable: str
    lower_bound: Optional[Dict[str, Any]] = None
    upper_bound: Optional[Dict[str, Any]] = None
    definite: bool = False
    measure: Optional[str] = None  # e.g. 'd^4x sqrt(-g)'


class TensorNode(BaseModel):
    kind: Literal["tensor"] = "tensor"
    name: str
    indices: List[str] = Field(default_factory=list)  # e.g. ["\mu", "\nu"]
    contravariant: List[bool] = Field(default_factory=list)  # True = upper, False = lower
    components: Optional[List[Any]] = None
    dimension: str = ""
    symmetry: Optional[str] = None

    def get_typed_indices(self) -> List[Any]:
        from automate.ir.tensors import TensorIndex
        typed = []
        for i, idx_str in enumerate(self.indices):
            is_upper = self.contravariant[i] if i < len(self.contravariant) else False
            typed.append(TensorIndex(
                symbol=idx_str.lstrip("\\"),
                position="upper" if is_upper else "lower"
            ))
        return typed


class ScalarNode(BaseModel):
    kind: Literal["scalar"] = "scalar"
    value: Union[int, float, str]
    dimension: str = ""
    is_constant: bool = False


class FieldNode(BaseModel):
    kind: Literal["field"] = "field"
    name: str
    field_type: Literal["scalar", "vector", "tensor", "spinor"] = "scalar"
    spacetime_coordinates: List[str] = Field(default_factory=lambda: ["t", "x", "y", "z"])
    dimension: str = ""
    indices: List[str] = Field(default_factory=list)


class OperatorNode(BaseModel):
    kind: Literal["operator"] = "operator"
    name: str
    symbol: str
    domain: str = "hilbert_space"
    is_hermitian: bool = True


class FunctionNode(BaseModel):
    kind: Literal["function"] = "function"
    name: str
    args: List[Dict[str, Any]] = Field(default_factory=list)


class LimitNode(BaseModel):
    kind: Literal["limit"] = "limit"
    expression: Dict[str, Any]
    variable: str
    target: str
    direction: Literal["both", "left", "right"] = "both"


class SumNode(BaseModel):
    kind: Literal["sum"] = "sum"
    summand: Dict[str, Any]
    index: str
    lower_bound: str
    upper_bound: str


class ProductNode(BaseModel):
    kind: Literal["product"] = "product"
    factor: Dict[str, Any]
    index: str
    lower_bound: str
    upper_bound: str


class ActionNode(BaseModel):
    kind: Literal["action"] = "action"
    name: str = "S"
    lagrangian_density: Dict[str, Any] = Field(default_factory=dict)
    measure: Dict[str, Any] = Field(default_factory=dict)
    boundary_terms: List[str] = Field(default_factory=list)
    dimension: str = "M*L^2*T^-1"


class MeasureNode(BaseModel):
    kind: Literal["measure"] = "measure"
    coordinates: List[str] = Field(default_factory=lambda: ["t", "x", "y", "z"])
    metric_determinant: str = "sqrt(-g)"
    dimension: str = "L^4"


class EquationNode(BaseModel):
    kind: Literal["equation"] = "equation"
    lhs: Dict[str, Any]
    rhs: Dict[str, Any]
    relation: Literal["eq", "neq", "lt", "gt", "leq", "geq"] = "eq"


class DifferentialEquationNode(BaseModel):
    kind: Literal["differential_equation"] = "differential_equation"
    equation: EquationNode
    independent_vars: List[str] = Field(default_factory=lambda: ["t"])
    dependent_vars: List[str] = Field(default_factory=lambda: ["x"])
    order: int = 2
    is_linear: bool = True



class TransformNode(BaseModel):
    """Canonical representation of a one-dimensional integral transform."""
    kind: Literal["transform"] = "transform"
    transform: Literal["fourier", "laplace"] 
    direction: Literal["forward", "inverse"] = "forward"
    expression: Dict[str, Any]
    source_variable: str
    target_variable: str
    convention: str
    assumptions: List[str] = Field(default_factory=list)

class FourierSeriesNode(BaseModel):
    """Fourier-series representation with explicit period and convention."""
    kind: Literal["fourier_series"] = "fourier_series"
    expression: Dict[str, Any]
    variable: str
    period: str
    coefficients: Dict[str, Any] = Field(default_factory=dict)
    interval: Optional[List[str]] = None
    assumptions: List[str] = Field(default_factory=list)

class ConvolutionNode(BaseModel):
    """Continuous convolution with explicit integration variable."""
    kind: Literal["convolution"] = "convolution"
    left: Dict[str, Any]
    right: Dict[str, Any]
    variable: str
    output_variable: str
    assumptions: List[str] = Field(default_factory=list)


class StatisticalModelNode(BaseModel):
    kind: Literal["statistical_model"] = "statistical_model"
    name: str
    distribution: str  # e.g. "normal"
    parameters: Dict[str, str]  # parameter name -> expression
    likelihood_expr: Optional[str] = None
    sample_data: Optional[List[float]] = None


class ObservableNode(BaseModel):
    kind: Literal["observable"] = "observable"
    name: str
    symbol: str
    expression: Dict[str, Any]
    dimension: str
    operator_form: Optional[str] = None


class MatrixNode(BaseModel):
    kind: Literal["matrix"] = "matrix"
    entries: List[List[Union[int, float, str]]] = Field(default_factory=list)
    dimension: str = ""
    coordinate_system: str = "matrix"

    @property
    def rows(self) -> int:
        return len(self.entries)

    @property
    def cols(self) -> int:
        return len(self.entries[0]) if self.entries else 0


class VectorNode(BaseModel):
    kind: Literal["vector"] = "vector"
    components: List[Dict[str, Any]]
    dimension: str = ""
    coordinate_system: str = "cartesian"


class PropositionNode(BaseModel):
    kind: Literal["proposition"] = "proposition"
    claim: str = Field(..., description="Proposition claim or theorem statement")
    hypotheses: List[str] = Field(default_factory=list, description="Explicit premises/hypotheses")
    formal_statement: Optional[str] = Field(default=None, description="Formal Lean/type statement")
    proof_obligation: Optional[str] = None


class PartialDifferentialEquationNode(BaseModel):
    kind: Literal["pde"] = "pde"
    equation: EquationNode
    independent_vars: List[str] = Field(default_factory=lambda: ["t", "x"])
    dependent_vars: List[str] = Field(default_factory=lambda: ["psi"])
    order: int = 2
    boundary_conditions: List[str] = Field(default_factory=list)


from enum import Enum


class IRNodeKind(str, Enum):
    EXPRESSION = "expression"
    EQUATION = "equation"
    PROPOSITION = "proposition"
    ASSUMPTION = "assumption"
    OBSERVABLE = "observable"
    PARAMETER = "parameter"
    TRAJECTORY = "trajectory"
    ACTION = "action"
    FIELD_EQUATION = "field_equation"
    TENSOR = "tensor"


class MathematicalExpression(BaseModel):
    """
    Unified expression wrapper storing canonical AST and multiple projections.
    """
    raw_str: str = Field(..., description="Canonical human-readable string representation")
    ast: Dict[str, Any] = Field(default_factory=dict, description="Typed AST dictionary")
    dimension: str = Field(default="", description="Overall physical dimension")
    latex: Optional[str] = None
    sympy_str: Optional[str] = None
    lean_str: Optional[str] = None

    @property
    def has_explicit_dimension(self) -> bool:
        """Whether physical dimension metadata was explicitly supplied."""
        return bool(self.dimension and self.dimension.strip())

    def get_dimension(self) -> Dimension:
        return Dimension.from_string(self.dimension)
