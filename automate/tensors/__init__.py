"""
Automate Tensor Algebra Module.

Provides symbolic component-level tensor computations and canonical tensor IR
utilities for external-engine verification.
"""

from automate.tensors.algebra import TensorGeometry
from automate.tensors.cadabra_translation import (
    tensor_expression_to_cadabra,
    tensor_product_to_cadabra,
    translate_expression,
)
from automate.tensors.cadabra_adapter import (
    get_cadabra_version,
    is_cadabra_available,
    run_cadabra_script,
)
from automate.ir.tensors import (
    TensorEquation,
    TensorExpression,
    TensorIndex,
    TensorProduct,
    TensorQuantity,
    validate_einstein_product,
    validate_tensor_equation,
    validate_tensor_sum,
)

__all__ = [
    "TensorGeometry",
    "tensor_expression_to_cadabra",
    "tensor_product_to_cadabra",
    "translate_expression",
    "get_cadabra_version",
    "is_cadabra_available",
    "run_cadabra_script",
    "TensorEquation",
    "TensorExpression",
    "TensorIndex",
    "TensorProduct",
    "TensorQuantity",
    "validate_einstein_product",
    "validate_tensor_equation",
    "validate_tensor_sum",
]
