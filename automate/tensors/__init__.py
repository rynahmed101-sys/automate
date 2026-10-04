"""
Automate Tensor Algebra Module.

Provides symbolic component-level tensor computations for Riemannian
and pseudo-Riemannian manifolds: Christoffel symbols, Riemann/Ricci tensors,
Ricci scalar, Einstein tensor, geodesic equations, and Bianchi identity verification.
"""

from automate.tensors.algebra import TensorGeometry
from automate.ir.tensors import (
    TensorEquation,
    TensorExpression,
    TensorIndex,
    TensorQuantity,
    validate_einstein_product,
    validate_tensor_equation,
    validate_tensor_sum,
)

__all__ = [
    "TensorGeometry",
    "TensorEquation",
    "TensorExpression",
    "TensorIndex",
    "TensorQuantity",
    "validate_einstein_product",
    "validate_tensor_equation",
    "validate_tensor_sum",
]
