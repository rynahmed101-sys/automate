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
    deriv_type: Literal["total", "partial", "time_dot"] = "total"
    order: int = 1


class IntegralNode(BaseModel):
    kind: Literal["integral"] = "integral"
    integrand: Dict[str, Any]
    variable: str
    lower_bound: Optional[Dict[str, Any]] = None
    upper_bound: Optional[Dict[str, Any]] = None
    definite: bool = False


class TensorNode(BaseModel):
    kind: Literal["tensor"] = "tensor"
    name: str
    indices: List[str]  # e.g. ["\mu", "\nu"]
    contravariant: List[bool] = Field(default_factory=list)  # True = upper, False = lower
    components: Optional[List[Any]] = None


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

    def get_dimension(self) -> Dimension:
        return Dimension.from_string(self.dimension)
