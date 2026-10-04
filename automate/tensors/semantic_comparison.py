"""Explicit tensor semantic metadata and independent SymPy canonicalization.

This module is deliberately conservative. It does not infer index spaces,
metrics, signatures, or tensor symmetries from names, dimensions, or syntax.
Missing required semantics produce UNSUPPORTED_SEMANTICS rather than an
equivalence claim.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from automate.ir.tensors import TensorEquation, TensorExpression, TensorIndex, TensorQuantity


class SemanticResult(str, Enum):
    SEMANTIC_MATCH = "SEMANTIC_MATCH"
    SEMANTIC_DISCREPANCY = "SEMANTIC_DISCREPANCY"
    UNSUPPORTED_SEMANTICS = "UNSUPPORTED_SEMANTICS"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    INVALID_IR = "INVALID_IR"


class IndexSpace(BaseModel):
    """Explicit index-space declaration."""

    name: str = Field(..., min_length=1)
    dimension: int = Field(..., gt=0)
    metric_name: Optional[str] = None
    metric_symmetry: Optional[Literal["symmetric", "antisymmetric"]] = None
    signature: Optional[Tuple[int, int]] = None


class TensorSymmetry(BaseModel):
    """Initial safe symmetry vocabulary."""

    kind: Literal["none", "symmetric", "antisymmetric", "riemann"] = "none"


class TensorSemanticContext(BaseModel):
    """Semantic declarations required before independent comparison."""

    index_spaces: List[IndexSpace] = Field(default_factory=list)

    def space_map(self) -> Dict[str, IndexSpace]:
        result = {space.name: space for space in self.index_spaces}
        if len(result) != len(self.index_spaces):
            raise ValueError("Index-space names must be unique.")
        return result


def validate_semantics(
    equation: TensorEquation, context: TensorSemanticContext
) -> List[str]:
    """Validate explicit semantics without guessing missing meaning."""
    errors: List[str] = []
    try:
        spaces = context.space_map()
    except ValueError as exc:
        return [str(exc)]

    if equation.lhs.products is None or equation.rhs.products is None:
        return ["Semantic comparison requires structured TensorProduct terms."]

    all_quantities: List[TensorQuantity] = []
    for expression in (equation.lhs, equation.rhs):
        for product in expression.products or []:
            all_quantities.extend(product.factors)

            for index in product.indices:
                if not index.index_space:
                    errors.append(
                        f"Index '{index.symbol}' is missing explicit index_space metadata."
                    )
                    continue
                space = spaces.get(index.index_space)
                if space is None:
                    errors.append(
                        f"Index '{index.symbol}' references unknown index space "
                        f"'{index.index_space}'."
                    )
                elif index.dimension is not None and index.dimension != space.dimension:
                    errors.append(
                        f"Index '{index.symbol}' dimension {index.dimension} does not "
                        f"match index space '{space.name}' dimension {space.dimension}."
                    )

    for quantity in all_quantities:
        kind = quantity.symmetry or "none"
        if kind not in {"none", "symmetric", "antisymmetric", "riemann"}:
            errors.append(
                f"Tensor '{quantity.name}' declares unsupported symmetry {kind!r}."
            )
            continue
        rank = len(quantity.indices)
        if kind in {"symmetric", "antisymmetric"} and rank < 2:
            errors.append(
                f"Tensor '{quantity.name}' has {kind} symmetry but rank {rank}; "
                "at least rank 2 is required."
            )
        if kind == "riemann" and rank != 4:
            errors.append(
                f"Tensor '{quantity.name}' declares riemann symmetry but rank is {rank}."
            )

    for expression in (equation.lhs, equation.rhs):
        by_symbol: Dict[str, List[TensorIndex]] = {}
        for product in expression.products or []:
            for factor in product.factors:
                for index in factor.indices:
                    by_symbol.setdefault(index.symbol, []).append(index)
        for symbol, occurrences in by_symbol.items():
            if len(occurrences) == 2:
                spaces_seen = {index.index_space for index in occurrences}
                if len(spaces_seen) != 1:
                    errors.append(
                        f"Contracted index '{symbol}' crosses incompatible index spaces: "
                        f"{sorted(spaces_seen)}."
                    )

    return errors


def _symmetry_for(quantity: TensorQuantity):
    from sympy.tensor.tensor import TensorSymmetry

    kind = quantity.symmetry or "none"
    rank = len(quantity.indices)
    if kind == "none":
        return TensorSymmetry.no_symmetry(rank)
    if kind == "symmetric":
        return TensorSymmetry.fully_symmetric(rank)
    if kind == "antisymmetric":
        return TensorSymmetry.fully_antisymmetric(rank)
    if kind == "riemann":
        return TensorSymmetry.riemann()
    raise ValueError(f"Unsupported tensor symmetry: {kind!r}")


def canonicalize_expression(
    expression: TensorExpression, context: TensorSemanticContext
) -> str:
    """Canonicalize through SymPy's independent tensor canonicalizer."""
    from sympy import Symbol
    from sympy.tensor.tensor import TensorHead, TensorIndex as SymTensorIndex, TensorIndexType

    if expression.products is None:
        raise ValueError("Independent semantic comparison requires structured products.")
    validation = expression.validate_structure()
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))

    spaces = context.space_map()
    sympy_spaces = {
        name: TensorIndexType(
            name,
            dim=space.dimension,
            metric_symmetry=1 if space.metric_symmetry == "symmetric" else None,
        )
        for name, space in spaces.items()
    }
    heads = {}
    indices = {}

    def get_index(index: TensorIndex):
        if not index.index_space:
            raise ValueError(f"Index '{index.symbol}' has no index space.")
        key = (index.symbol, index.index_space)
        if key not in indices:
            indices[key] = SymTensorIndex(
                index.symbol, sympy_spaces[index.index_space]
            )
        return indices[key] if index.position == "upper" else -indices[key]

    def get_head(quantity: TensorQuantity):
        key = (
            quantity.name,
            tuple(index.index_space for index in quantity.indices),
            quantity.symmetry or "none",
        )
        if key not in heads:
            heads[key] = TensorHead(
                quantity.name,
                [sympy_spaces[index.index_space] for index in quantity.indices],
                _symmetry_for(quantity),
            )
        return heads[key]

    terms = []
    for product in expression.products:
        factors = []
        for quantity in product.factors:
            if not quantity.indices:
                factors.append(Symbol(quantity.name))
            else:
                factors.append(
                    get_head(quantity)(
                        *[get_index(index) for index in quantity.indices]
                    )
                )
        if not factors:
            raise ValueError("Tensor products cannot be empty.")
        term = factors[0]
        for factor in factors[1:]:
            term = term * factor
        terms.append(term)

    result = terms[0]
    for term in terms[1:]:
        result = result + term
    return str(result.canon_bp())


def semantic_signature(expression: TensorExpression) -> str:
    """Return an explicit semantic declaration fingerprint.

    SymPy canonicalization is responsible for tensor canonicalization, while
    this independent metadata fingerprint preserves distinctions such as two
    same-dimensional but different index spaces that a rendered canonical
    expression may not expose.
    """
    if expression.products is None:
        raise ValueError("Semantic comparison requires structured products.")
    payload = []
    for product in expression.products:
        factors = []
        for quantity in product.factors:
            factors.append({
                "name": quantity.name,
                "symmetry": quantity.symmetry or "none",
                "indices": [
                    {
                        "symbol": index.symbol,
                        "index_space": index.index_space,
                        "position": index.position,
                        "dimension": index.dimension,
                    }
                    for index in quantity.indices
                ],
            })
        payload.append({"factors": factors})
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def semantic_compare(
    left: TensorEquation,
    right: TensorEquation,
    context: TensorSemanticContext,
) -> dict:
    """Compare two semantic tensor equations through independent SymPy."""
    try:
        left_errors = validate_semantics(left, context)
        right_errors = validate_semantics(right, context)
    except Exception as exc:
        return {
            "result": SemanticResult.INVALID_IR.value,
            "reason": str(exc),
            "independence_class": "INDEPENDENT_ENGINE",
        }

    if left_errors or right_errors:
        return {
            "result": SemanticResult.UNSUPPORTED_SEMANTICS.value,
            "left_errors": left_errors,
            "right_errors": right_errors,
            "independence_class": "INDEPENDENT_ENGINE",
        }

    try:
        left_canonical = (
            canonicalize_expression(left.lhs, context),
            canonicalize_expression(left.rhs, context),
        )
        right_canonical = (
            canonicalize_expression(right.lhs, context),
            canonicalize_expression(right.rhs, context),
        )
        left_semantics = (semantic_signature(left.lhs), semantic_signature(left.rhs))
        right_semantics = (semantic_signature(right.lhs), semantic_signature(right.rhs))
    except Exception as exc:
        return {
            "result": SemanticResult.EXECUTION_FAILED.value,
            "reason": str(exc),
            "independence_class": "INDEPENDENT_ENGINE",
        }

    left_payload = json.dumps({"canonical": left_canonical, "semantics": left_semantics}, separators=(",", ":"), sort_keys=True)
    right_payload = json.dumps({"canonical": right_canonical, "semantics": right_semantics}, separators=(",", ":"), sort_keys=True)
    left_fp = hashlib.sha256(left_payload.encode()).hexdigest()
    right_fp = hashlib.sha256(right_payload.encode()).hexdigest()
    matched = left_canonical == right_canonical
    return {
        "result": (
            SemanticResult.SEMANTIC_MATCH.value
            if matched
            else SemanticResult.SEMANTIC_DISCREPANCY.value
        ),
        "independence_class": "INDEPENDENT_ENGINE",
        "engine": "SymPy",
        "canonicalization": "TensorIndexType/TensorHead/TensorSymmetry/canon_bp",
        "left_fingerprint_sha256": left_fp,
        "right_fingerprint_sha256": right_fp,
        "canonical_equal": matched,
    }
