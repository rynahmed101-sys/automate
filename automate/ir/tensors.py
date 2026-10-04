"""Canonical Tensor Semantics, Einstein Contraction, and Index Validation for Automate IR."""

from typing import List, Dict, Any, Optional, Tuple, Literal
from collections import Counter
from pydantic import BaseModel, Field


class TensorIndex(BaseModel):
    """A single tensor index with explicit variance and optional cardinality."""
    symbol: str = Field(..., description="Index symbol or identifier")
    dimension: Optional[int] = Field(default=None, gt=0)
    position: Literal["upper", "lower"] = Field(default="lower")
    is_dummy: bool = Field(default=False)

    @property
    def variance(self) -> str:
        return "contravariant" if self.position == "upper" else "covariant"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TensorIndex):
            return (
                self.symbol == other.symbol
                and self.position == other.position
                and self.dimension == other.dimension
            )
        return False

    def __hash__(self) -> int:
        return hash((self.symbol, self.position, self.dimension))


class TensorQuantity(BaseModel):
    """A named tensor with ordered indices and optional symmetry metadata."""
    name: str = Field(..., description="Tensor name, e.g. g, R, T")
    indices: List[TensorIndex] = Field(default_factory=list)
    dimension: str = Field(default="")
    symmetry: Optional[str] = Field(default=None)
    latex: Optional[str] = None

    @property
    def rank(self) -> int:
        return len(self.free_indices)

    @property
    def free_indices(self) -> List[TensorIndex]:
        return [idx for idx in self.indices if not idx.is_dummy]

    @property
    def dummy_indices(self) -> List[TensorIndex]:
        return [idx for idx in self.indices if idx.is_dummy]


class TensorProduct(BaseModel):
    """Ordered product of named tensor quantities.

    This is the minimal semantic bridge needed by external symbolic engines:
    TensorExpression intentionally describes sums of index-bearing terms, but
    historically did not retain tensor-factor names. A product retains those
    names without changing the legacy expression model.
    """
    factors: List[TensorQuantity] = Field(..., min_length=1)

    @property
    def indices(self) -> List[TensorIndex]:
        return [idx for factor in self.factors for idx in factor.indices]

    def validate_structure(self) -> "IndexValidationResult":
        return validate_einstein_product(self.indices)


class TensorExpression(BaseModel):
    """Structured sum of tensor products.

    Legacy callers may still pass List[List[TensorIndex]], which is normalized
    as an unnamed index term. New external-engine translation should use
    TensorProduct terms so tensor factor identity is preserved.
    """
    terms: List[List[TensorIndex]] = Field(..., min_length=1)
    products: Optional[List[TensorProduct]] = None

    def validate_structure(self) -> "IndexValidationResult":
        if self.products is not None:
            if len(self.products) != len(self.terms):
                return IndexValidationResult(
                    is_valid=False,
                    errors=["TensorExpression products and terms must have equal length."],
                )
            product_results = [product.validate_structure() for product in self.products]
            for i, product in enumerate(self.products):
                expected = [
                    (index.symbol, index.position, index.dimension)
                    for index in product.indices
                ]
                supplied = [
                    (index.symbol, index.position, index.dimension)
                    for index in self.terms[i]
                ]
                if expected != supplied:
                    return IndexValidationResult(
                        is_valid=False,
                        errors=[
                            f"Term {i+1} products and legacy terms disagree on "
                            "index identity/variance/dimension."
                        ],
                    )
            for i, result in enumerate(product_results):
                if not result.is_valid:
                    return IndexValidationResult(
                        is_valid=False,
                        errors=[f"Term {i+1} has invalid internal index structure: {'; '.join(result.errors)}"],
                    )
            return _validate_free_signatures(
                [result.free_indices for result in product_results]
            )
        return validate_tensor_sum(self.terms)

    @property
    def free_index_signature(self) -> List[Tuple[str, str, Optional[int]]]:
        result = self.validate_structure()
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return sorted(
            (index.symbol, index.position, index.dimension)
            for index in result.free_indices
        )


class TensorEquation(BaseModel):
    """Structured tensor equation with independently validated sides."""
    lhs: TensorExpression
    rhs: TensorExpression

    def validate_structure(self) -> "IndexValidationResult":
        if self.lhs.products is not None or self.rhs.products is not None:
            if self.lhs.products is None or self.rhs.products is None:
                return IndexValidationResult(
                    is_valid=False,
                    errors=["TensorEquation requires structured products on both sides."],
                )
            lhs_validation = self.lhs.validate_structure()
            rhs_validation = self.rhs.validate_structure()
            errors = [
                *[f"LHS index error: {error}" for error in lhs_validation.errors],
                *[f"RHS index error: {error}" for error in rhs_validation.errors],
            ]
            if errors:
                return IndexValidationResult(is_valid=False, errors=errors)
            lhs_free = {
                (index.symbol, index.position, index.dimension)
                for index in lhs_validation.free_indices
            }
            rhs_free = {
                (index.symbol, index.position, index.dimension)
                for index in rhs_validation.free_indices
            }
            if lhs_free != rhs_free:
                errors.append(
                    "Equation index mismatch between LHS and RHS. "
                    f"LHS free indices: {sorted(lhs_free)}; RHS free indices: {sorted(rhs_free)}."
                )
            return IndexValidationResult(
                is_valid=not errors,
                free_indices=lhs_validation.free_indices if not errors else [],
                resultant_rank=lhs_validation.resultant_rank if not errors else -1,
                errors=errors,
            )

        lhs_indices = [index for term in self.lhs.terms for index in term]
        rhs_indices = [index for term in self.rhs.terms for index in term]
        return validate_tensor_equation(lhs_indices, rhs_indices)

    @property
    def free_index_signature(self) -> List[Tuple[str, str, Optional[int]]]:
        result = self.validate_structure()
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return sorted(
            (index.symbol, index.position, index.dimension)
            for index in result.free_indices
        )


class IndexValidationResult(BaseModel):
    """Result of Einstein index validation."""
    is_valid: bool
    free_indices: List[TensorIndex] = Field(default_factory=list)
    dummy_indices: List[str] = Field(default_factory=list)
    resultant_rank: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def validate_einstein_product(indices: List[TensorIndex]) -> IndexValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    symbol_counts = Counter(idx.symbol for idx in indices)
    symbol_positions: Dict[str, List[str]] = {}
    symbol_dimensions: Dict[str, List[Optional[int]]] = {}
    for idx in indices:
        symbol_positions.setdefault(idx.symbol, []).append(idx.position)
        symbol_dimensions.setdefault(idx.symbol, []).append(idx.dimension)

    free_indices: List[TensorIndex] = []
    dummy_indices: List[str] = []
    for sym, count in symbol_counts.items():
        positions = symbol_positions[sym]
        if count == 1:
            free_idx = next(idx for idx in indices if idx.symbol == sym)
            free_indices.append(TensorIndex(
                symbol=sym, position=positions[0], dimension=free_idx.dimension
            ))
        elif count == 2:
            dimensions = {d for d in symbol_dimensions[sym] if d is not None}
            if len(dimensions) > 1:
                errors.append(
                    f"Invalid contraction on index '{sym}': incompatible index dimensions {sorted(dimensions)}."
                )
            if positions[0] == positions[1]:
                errors.append(
                    f"Invalid contraction on index '{sym}': both occurrences are in '{positions[0]}' position. "
                    "Einstein summation requires one upper and one lower index."
                )
            else:
                dummy_indices.append(sym)
        else:
            errors.append(
                f"Illegal repeated index '{sym}' appears {count} times. Einstein summation allows at most 2 occurrences."
            )

    is_valid = not errors
    return IndexValidationResult(
        is_valid=is_valid,
        free_indices=free_indices if is_valid else [],
        dummy_indices=dummy_indices if is_valid else [],
        resultant_rank=len(free_indices) if is_valid else -1,
        errors=errors,
        warnings=warnings,
    )


def _validate_free_signatures(
    free_lists: List[List[TensorIndex]],
) -> IndexValidationResult:
    if not free_lists:
        return IndexValidationResult(is_valid=True, resultant_rank=0)
    reference = {(i.symbol, i.position, i.dimension) for i in free_lists[0]}
    errors = []
    for n, indices in enumerate(free_lists[1:], start=2):
        current = {(i.symbol, i.position, i.dimension) for i in indices}
        if current != reference:
            errors.append(
                f"Free index mismatch between term 1 and term {n}. "
                f"Term 1 free indices: {sorted(reference)}; Term {n} free indices: {sorted(current)}."
            )
    return IndexValidationResult(
        is_valid=not errors,
        free_indices=free_lists[0] if not errors else [],
        resultant_rank=len(free_lists[0]) if not errors else -1,
        errors=errors,
    )


def validate_tensor_sum(terms_indices: List[List[TensorIndex]]) -> IndexValidationResult:
    if not terms_indices:
        return IndexValidationResult(is_valid=True, resultant_rank=0)
    term_results = [validate_einstein_product(term) for term in terms_indices]
    for i, tr in enumerate(term_results):
        if not tr.is_valid:
            return IndexValidationResult(
                is_valid=False,
                errors=[f"Term {i+1} has invalid internal index structure: {'; '.join(tr.errors)}"],
            )
    return _validate_free_signatures([r.free_indices for r in term_results])


def validate_tensor_equation(
    lhs_indices: List[TensorIndex], rhs_indices: List[TensorIndex]
) -> IndexValidationResult:
    lhs_res = validate_einstein_product(lhs_indices)
    rhs_res = validate_einstein_product(rhs_indices)
    errors = []
    if not lhs_res.is_valid:
        errors.extend([f"LHS index error: {e}" for e in lhs_res.errors])
    if not rhs_res.is_valid:
        errors.extend([f"RHS index error: {e}" for e in rhs_res.errors])
    if errors:
        return IndexValidationResult(is_valid=False, errors=errors)
    lhs_free = {(i.symbol, i.position, i.dimension) for i in lhs_res.free_indices}
    rhs_free = {(i.symbol, i.position, i.dimension) for i in rhs_res.free_indices}
    if lhs_free != rhs_free:
        errors.append(
            f"Equation index mismatch between LHS and RHS. "
            f"LHS free indices: {sorted(lhs_free)}; RHS free indices: {sorted(rhs_free)}."
        )
    return IndexValidationResult(
        is_valid=not errors,
        free_indices=lhs_res.free_indices if not errors else [],
        resultant_rank=lhs_res.resultant_rank if not errors else -1,
        errors=errors,
    )
