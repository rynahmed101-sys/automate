"""
Automate Tensor Algebra Module.

Provides symbolic component-level tensor computations for Riemannian
and pseudo-Riemannian manifolds: Christoffel symbols, Riemann/Ricci tensors,
Ricci scalar, Einstein tensor, geodesic equations, and Bianchi identity verification.
"""

from automate.tensors.algebra import TensorGeometry
from automate.tensors.index import (
    TensorExpression,
    TensorFactor,
    TensorIndex,
    TensorSymbol,
    TensorTerm,
    validate_tensor_equation,
)

__all__ = [
    "TensorGeometry",
    "TensorExpression",
    "TensorFactor",
    "TensorIndex",
    "TensorSymbol",
    "TensorTerm",
    "validate_tensor_equation",
]
