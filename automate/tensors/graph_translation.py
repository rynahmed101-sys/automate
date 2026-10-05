"""Strict conversion from graph MathematicalExpression ASTs to canonical Tensor IR.

This adapter is intentionally loss-averse: only AST constructs that can be
represented without guessing semantics are accepted. Raw strings are never
parsed as a fallback, and index dimensions are never inferred from tensor
physical dimensions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from automate.core.graph import DerivationGraph
from automate.ir.tensors import (
    TensorEquation,
    TensorExpression,
    TensorIndex,
    TensorProduct,
    TensorQuantity,
)


def _require_mapping(node: Any, context: str) -> Dict[str, Any]:
    if not isinstance(node, dict):
        raise ValueError(f"{context} must be a dictionary AST node.")
    kind = node.get("kind")
    if not isinstance(kind, str):
        raise ValueError(f"{context} is missing a string 'kind'.")
    return node


def _tensor_quantity(node: Dict[str, Any], context: str) -> TensorQuantity:
    node = _require_mapping(node, context)
    if node.get("kind") != "tensor":
        raise ValueError(f"{context} must be a tensor AST node.")

    name = node.get("name")
    indices = node.get("indices", [])
    contravariant = node.get("contravariant", [])
    if not isinstance(name, str) or not name:
        raise ValueError(f"{context}.name must be a non-empty string.")
    if not isinstance(indices, list) or not isinstance(contravariant, list):
        raise ValueError(f"{context} tensor indices must be lists.")
    if len(contravariant) > len(indices):
        raise ValueError(f"{context}.contravariant cannot exceed indices length.")

    typed: List[TensorIndex] = []
    for position, symbol in enumerate(indices):
        if not isinstance(symbol, str) or not symbol:
            raise ValueError(f"{context}.indices[{position}] must be a non-empty string.")
        upper = contravariant[position] if position < len(contravariant) else False
        if not isinstance(upper, bool):
            raise ValueError(f"{context}.contravariant[{position}] must be boolean.")
        typed.append(
            TensorIndex(
                symbol=symbol.lstrip("\\"),
                position="upper" if upper else "lower",
            )
        )

    return TensorQuantity(
        name=name,
        indices=typed,
        dimension=str(node.get("dimension", "")),
        symmetry=node.get("symmetry"),
    )


def _products_from_ast(node: Any, context: str) -> List[List[TensorQuantity]]:
    node = _require_mapping(node, context)
    kind = node["kind"]

    if kind == "tensor":
        return [[_tensor_quantity(node, context)]]

    if kind == "symbol":
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{context}.name must be a non-empty string.")
        return [[TensorQuantity(name=name, dimension=str(node.get("dimension", "")))]]

    if kind == "binary_op":
        op = node.get("op")
        left = _products_from_ast(node.get("left"), f"{context}.left")
        right = _products_from_ast(node.get("right"), f"{context}.right")
        if op == "add":
            return [*left, *right]
        if op == "mul":
            return [left_term + right_term for left_term in left for right_term in right]
        raise ValueError(
            f"{context} uses unsupported binary operation {op!r}; "
            "Tensor IR conversion supports only addition and multiplication."
        )

    raise ValueError(
        f"{context} uses unsupported AST kind {kind!r}; "
        "Tensor IR conversion is deliberately strict."
    )


def mathematical_expression_to_tensor_ir(expression: Any) -> TensorExpression:
    """Convert one graph MathematicalExpression to validated TensorExpression."""
    ast = getattr(expression, "ast", None)
    if not ast:
        raise ValueError(
            "Graph tensor conversion requires a populated MathematicalExpression.ast; "
            "raw expression text is not parsed implicitly."
        )

    products = [
        TensorProduct(factors=factors)
        for factors in _products_from_ast(ast, "expression.ast")
    ]
    terms = [[index for factor in product.factors for index in factor.indices] for product in products]
    result = TensorExpression(terms=terms, products=products)
    validation = result.validate_structure()
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))
    return result


def graph_node_to_tensor_ir(graph: DerivationGraph, node_id: str) -> TensorExpression:
    """Convert a named graph node's structured AST into canonical Tensor IR."""
    node = graph.get_node(node_id)
    if node is None:
        raise KeyError(f"Graph node '{node_id}' not found.")
    return mathematical_expression_to_tensor_ir(node.expression)


def graph_equation_node_to_tensor_ir(
    graph: DerivationGraph, node_id: str
) -> TensorEquation:
    """Convert a graph equation AST node into a validated TensorEquation."""
    node = graph.get_node(node_id)
    if node is None:
        raise KeyError(f"Graph node '{node_id}' not found.")

    ast = node.expression.ast
    if not isinstance(ast, dict) or ast.get("kind") != "equation":
        raise ValueError(
            f"Graph node '{node_id}' does not contain an equation AST."
        )

    lhs_products = [
        TensorProduct(factors=factors)
        for factors in _products_from_ast(ast.get("lhs"), "equation.lhs")
    ]
    rhs_products = [
        TensorProduct(factors=factors)
        for factors in _products_from_ast(ast.get("rhs"), "equation.rhs")
    ]
    lhs = TensorExpression(
        terms=[[i for f in p.factors for i in f.indices] for p in lhs_products],
        products=lhs_products,
    )
    rhs = TensorExpression(
        terms=[[i for f in p.factors for i in f.indices] for p in rhs_products],
        products=rhs_products,
    )
    equation = TensorEquation(lhs=lhs, rhs=rhs)
    validation = equation.validate_structure()
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))
    return equation
