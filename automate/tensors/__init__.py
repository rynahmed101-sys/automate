"""
Automate Tensor Algebra Module.

Provides symbolic component-level tensor computations and canonical tensor IR
utilities for external-engine verification.
"""

from automate.tensors.algebra import TensorGeometry
from automate.tensors.cadabra_translation import (
    tensor_equation_to_cadabra,
    tensor_expression_to_cadabra,
    tensor_product_to_cadabra,
    translate_equation,
    translate_expression,
)
from automate.tensors.cadabra_verification import (
    independent_structural_equation_result,
    independent_structural_result,
    verify_graph_tensor_equation_with_cadabra,
    verify_graph_tensor_node_with_cadabra,
    verify_translated_equation,
    verify_translated_expression,
)
from automate.tensors.graph_translation import (
    graph_equation_node_to_tensor_ir,
    graph_node_to_tensor_ir,
    mathematical_expression_to_tensor_ir,
)
from automate.tensors.cadabra_adapter import (
    get_cadabra_version,
    is_cadabra_available,
    run_cadabra_script,
    run_translated_cadabra,
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
    "tensor_equation_to_cadabra",
    "tensor_expression_to_cadabra",
    "tensor_product_to_cadabra",
    "translate_equation",
    "translate_expression",
    "get_cadabra_version",
    "is_cadabra_available",
    "run_cadabra_script",
    "run_translated_cadabra",
    "independent_structural_equation_result",
    "independent_structural_result",
    "verify_translated_equation",
    "verify_translated_expression",
    "verify_graph_tensor_equation_with_cadabra",
    "verify_graph_tensor_node_with_cadabra",
    "graph_equation_node_to_tensor_ir",
    "graph_node_to_tensor_ir",
    "mathematical_expression_to_tensor_ir",
    "TensorEquation",
    "TensorExpression",
    "TensorIndex",
    "TensorProduct",
    "TensorQuantity",
    "validate_einstein_product",
    "validate_tensor_equation",
    "validate_tensor_sum",
]
