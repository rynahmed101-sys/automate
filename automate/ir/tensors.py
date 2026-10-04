"""
Canonical Tensor Semantics, Einstein Contraction, and Index Validation for Automate IR.
Enforces strict relativistic and differential geometric index rules:
- Free index consistency across addition and equations
- Dummy index pairing (exactly one contravariant and one covariant)
- Prohibition of illegal repeated dummy indices (>2 occurrences)
- Explicit contraction rank computation (e.g. R_{mu nu} g^{mu nu} -> scalar rank 0)
"""

from typing import List, Dict, Any, Optional, Tuple, Set, Literal
from collections import Counter
from pydantic import BaseModel, Field


class TensorIndex(BaseModel):
    """
    A single index on a tensor or geometric quantity.

    dimension is the coordinate/index-space cardinality when known. It is
    separate from TensorQuantity.dimension, which describes physical units.
    """
    symbol: str = Field(..., description="Index symbol or identifier, e.g. 'mu', 'nu', 'i', '0'")
    dimension: Optional[int] = Field(
        default=None,
        gt=0,
        description="Optional dimension/cardinality of the index space",
    )
    position: Literal["upper", "lower"] = Field(
        default="lower",
        description="'upper' for contravariant, 'lower' for covariant"
    )
    is_dummy: bool = Field(
        default=False,
        description="Whether this index is a summed dummy index in Einstein convention"
    )

    @property
    def variance(self) -> str:
        return "contravariant" if self.position == "upper" else "covariant"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TensorIndex):
            return self.symbol == other.symbol and self.position == other.position
        return False

    def __hash__(self) -> int:
        return hash((self.symbol, self.position))


class TensorExpression(BaseModel):
    """
    Structured sum of tensor index terms.

    Each term is represented by the ordered indices carried by its tensor
    factors. Validation derives free/dummy status from repeated labels instead
    of trusting caller-supplied is_dummy flags.
    """
    terms: List[List[TensorIndex]] = Field(..., min_length=1)

    def validate_structure(self) -> "IndexValidationResult":
        return validate_tensor_sum(self.terms)

    @property
    def free_index_signature(self) -> List[Tuple[str, str]]:
        result = self.validate_structure()
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return sorted(
            (index.symbol, index.position)
            for index in result.free_indices
        )


class TensorEquation(BaseModel):
    """Structured tensor equation with independently validated sides."""

    lhs: TensorExpression
    rhs: TensorExpression

    def validate_structure(self) -> "IndexValidationResult":
        lhs_indices = [index for term in self.lhs.terms for index in term]
        rhs_indices = [index for term in self.rhs.terms for index in term]
        return validate_tensor_equation(lhs_indices, rhs_indices)

    @property
    def free_index_signature(self) -> List[Tuple[str, str]]:
        result = self.validate_structure()
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return sorted(
            (index.symbol, index.position)
            for index in result.free_indices
        )


class TensorQuantity(BaseModel):
    """
    A typed tensor with explicit rank, indices, and symmetries.
    """
    name: str = Field(..., description="Tensor name, e.g. 'g', 'R', 'T', 'F', 'A'")
    indices: List[TensorIndex] = Field(default_factory=list, description="Ordered tensor indices")
    dimension: str = Field(default="", description="Physical dimension string")
    symmetry: Optional[str] = Field(
        default=None,
        description="Known symmetry: 'symmetric', 'antisymmetric', 'metric', 'riemann'"
    )
    latex: Optional[str] = None

    @property
    def rank(self) -> int:
        return len(self.free_indices)

    @property
    def free_indices(self) -> List[TensorIndex]:
        """Free (uncontracted) indices."""
        return [idx for idx in self.indices if not idx.is_dummy]

    @property
    def dummy_indices(self) -> List[TensorIndex]:
        """Contracted dummy indices."""
        return [idx for idx in self.indices if idx.is_dummy]


class IndexValidationResult(BaseModel):
    """
    Result of Einstein index validation.
    """
    is_valid: bool
    free_indices: List[TensorIndex] = Field(default_factory=list)
    dummy_indices: List[str] = Field(default_factory=list)
    resultant_rank: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def validate_einstein_product(indices: List[TensorIndex]) -> IndexValidationResult:
    """
    Validates Einstein summation rules on a product of tensors:
    1. Each index symbol may appear at most twice.
    2. If a symbol appears twice, one must be upper and one must be lower.
    3. If a symbol appears once, it is a free index.
    """
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
            free_indices.append(TensorIndex(symbol=sym, position=positions[0], is_dummy=False))
        elif count == 2:
            dimensions = {
                dimension
                for dimension in symbol_dimensions[sym]
                if dimension is not None
            }
            if len(dimensions) > 1:
                errors.append(
                    f"Invalid contraction on index '{sym}': incompatible index dimensions "
                    f"{sorted(dimensions)}."
                )
            if positions[0] == positions[1]:
                errors.append(
                    f"Invalid contraction on index '{sym}': both occurrences are in '{positions[0]}' position. "
                    "Einstein summation requires one upper (contravariant) and one lower (covariant) index."
                )
            else:
                dummy_indices.append(sym)
        else:
            errors.append(
                f"Illegal repeated index '{sym}' appears {count} times. "
                "Einstein summation allows at most 2 occurrences (one upper, one lower)."
            )

    is_valid = len(errors) == 0
    return IndexValidationResult(
        is_valid=is_valid,
        free_indices=free_indices if is_valid else [],
        dummy_indices=dummy_indices if is_valid else [],
        resultant_rank=len(free_indices) if is_valid else -1,
        errors=errors,
        warnings=warnings
    )


def validate_tensor_sum(terms_indices: List[List[TensorIndex]]) -> IndexValidationResult:
    """
    Validates that all terms in a sum or difference have identical free index structures.
    e.g. R_{mu nu} + T_{mu nu} is valid.
    R_{mu nu} + T_mu is invalid.
    """
    if not terms_indices:
        return IndexValidationResult(is_valid=True, resultant_rank=0)

    # First validate each individual term
    term_results = [validate_einstein_product(term) for term in terms_indices]
    for i, tr in enumerate(term_results):
        if not tr.is_valid:
            return IndexValidationResult(
                is_valid=False,
                errors=[f"Term {i+1} has invalid internal index structure: {'; '.join(tr.errors)}"]
            )

    # Compare free indices of all terms to the first term
    reference_free = set((idx.symbol, idx.position) for idx in term_results[0].free_indices)
    errors: List[str] = []

    for i in range(1, len(term_results)):
        curr_free = set((idx.symbol, idx.position) for idx in term_results[i].free_indices)
        if curr_free != reference_free:
            errors.append(
                f"Free index mismatch between term 1 and term {i+1}. "
                f"Term 1 free indices: {sorted(list(reference_free))}; "
                f"Term {i+1} free indices: {sorted(list(curr_free))}."
            )

    is_valid = len(errors) == 0
    return IndexValidationResult(
        is_valid=is_valid,
        free_indices=term_results[0].free_indices if is_valid else [],
        resultant_rank=len(term_results[0].free_indices) if is_valid else -1,
        errors=errors
    )


def validate_tensor_equation(lhs_indices: List[TensorIndex], rhs_indices: List[TensorIndex]) -> IndexValidationResult:
    """
    Validates that LHS and RHS of a tensor equation share the exact same free indices and rank.
    e.g. G_{mu nu} + Lambda g_{mu nu} = 8 pi G T_{mu nu} is valid (rank 2, both mu, nu lower).
    G_{mu nu} = 8 pi G T_mu is invalid.
    """
    lhs_res = validate_einstein_product(lhs_indices)
    rhs_res = validate_einstein_product(rhs_indices)

    errors = []
    if not lhs_res.is_valid:
        errors.extend([f"LHS index error: {e}" for e in lhs_res.errors])
    if not rhs_res.is_valid:
        errors.extend([f"RHS index error: {e}" for e in rhs_res.errors])

    if errors:
        return IndexValidationResult(is_valid=False, errors=errors)

    lhs_free = set((idx.symbol, idx.position) for idx in lhs_res.free_indices)
    rhs_free = set((idx.symbol, idx.position) for idx in rhs_res.free_indices)

    if lhs_free != rhs_free:
        errors.append(
            f"Equation index mismatch between LHS and RHS. "
            f"LHS free indices: {sorted(list(lhs_free))}; "
            f"RHS free indices: {sorted(list(rhs_free))}."
        )

    is_valid = len(errors) == 0
    return IndexValidationResult(
        is_valid=is_valid,
        free_indices=lhs_res.free_indices if is_valid else [],
        resultant_rank=lhs_res.resultant_rank if is_valid else -1,
        errors=errors
    )
