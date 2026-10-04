"""Structured tensor/index semantics for machine-auditable Einstein notation.

This module validates index variance, contraction rules, tensor rank, and
free-index compatibility without performing tensor component calculations.
It is intentionally separate from TensorGeometry so component computation can
adopt the semantic layer incrementally.
"""

from __future__ import annotations

from collections import Counter
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


IndexVariance = Literal["up", "down"]


class TensorIndex(BaseModel):
    """One tensor index with explicit variance and optional dimension."""

    label: str = Field(..., min_length=1)
    variance: IndexVariance
    dimension: Optional[int] = Field(default=None, gt=0)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tensor index label must not be empty.")
        if not value.replace("_", "").isalnum() or value[0].isdigit():
            raise ValueError(
                "Tensor index labels must be identifier-like strings, e.g. 'mu' or 'i'."
            )
        return value


class TensorSymbol(BaseModel):
    """Tensor declaration with explicit rank and slot variance."""

    name: str = Field(..., min_length=1)
    variance: List[IndexVariance]
    dimensions: List[Optional[int]] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tensor name must not be empty.")
        return value

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value: List[Optional[int]]) -> List[Optional[int]]:
        for dimension in value:
            if dimension is not None and dimension <= 0:
                raise ValueError("Tensor slot dimensions must be positive when provided.")
        return value

    @property
    def rank(self) -> int:
        return len(self.variance)


class TensorFactor(BaseModel):
    """A tensor symbol applied to an ordered list of explicit indices."""

    tensor: TensorSymbol
    indices: List[TensorIndex]

    def validate_shape_and_variance(self) -> None:
        if len(self.indices) != self.tensor.rank:
            raise ValueError(
                f"Tensor '{self.tensor.name}' has rank {self.tensor.rank} but "
                f"{len(self.indices)} indices were supplied."
            )

        if self.tensor.dimensions and len(self.tensor.dimensions) != self.tensor.rank:
            raise ValueError(
                f"Tensor '{self.tensor.name}' dimensions must match its rank."
            )

        for position, (slot_variance, index) in enumerate(
            zip(self.tensor.variance, self.indices)
        ):
            if slot_variance != index.variance:
                raise ValueError(
                    f"Tensor '{self.tensor.name}' slot {position} expects "
                    f"{slot_variance} variance, got {index.variance}."
                )
            expected_dimension = (
                self.tensor.dimensions[position]
                if self.tensor.dimensions
                else None
            )
            if (
                expected_dimension is not None
                and index.dimension is not None
                and expected_dimension != index.dimension
            ):
                raise ValueError(
                    f"Tensor '{self.tensor.name}' slot {position} expects "
                    f"dimension {expected_dimension}, got {index.dimension}."
                )

    def __init__(self, **data):
        super().__init__(**data)
        self.validate_shape_and_variance()


class TensorTerm(BaseModel):
    """A monomial product of tensor factors with Einstein index validation."""

    factors: List[TensorFactor] = Field(default_factory=list)

    def validate_einstein_summation(self) -> None:
        occurrences = {}
        for factor in self.factors:
            factor.validate_shape_and_variance()
            for index in factor.indices:
                occurrences.setdefault(index.label, []).append(index)

        for label, indices in occurrences.items():
            if len(indices) > 2:
                raise ValueError(
                    f"Index '{label}' occurs {len(indices)} times; Einstein "
                    "summation permits at most two occurrences in a term."
                )
            if len(indices) == 2:
                variances = {index.variance for index in indices}
                if variances != {"up", "down"}:
                    raise ValueError(
                        f"Repeated index '{label}' must occur once up and once down."
                    )
                dimensions = {
                    index.dimension for index in indices if index.dimension is not None
                }
                if len(dimensions) > 1:
                    raise ValueError(
                        f"Contracted index '{label}' has incompatible dimensions: "
                        f"{sorted(dimensions)}."
                    )

    @property
    def free_indices(self) -> List[TensorIndex]:
        self.validate_einstein_summation()
        occurrences = {}
        for factor in self.factors:
            for index in factor.indices:
                occurrences.setdefault(index.label, []).append(index)
        return [
            indices[0]
            for label, indices in occurrences.items()
            if len(indices) == 1
        ]

    @property
    def contracted_labels(self) -> List[str]:
        self.validate_einstein_summation()
        counts = Counter(
            index.label
            for factor in self.factors
            for index in factor.indices
        )
        return sorted(label for label, count in counts.items() if count == 2)

    def free_index_signature(self) -> List[Tuple[str, str, Optional[int]]]:
        return sorted(
            (index.label, index.variance, index.dimension)
            for index in self.free_indices
        )


class TensorExpression(BaseModel):
    """A sum of tensor terms that must share one free-index signature."""

    terms: List[TensorTerm] = Field(..., min_length=1)

    def validate_index_structure(self) -> List[Tuple[str, str, Optional[int]]]:
        signatures = []
        for term in self.terms:
            term.validate_einstein_summation()
            signatures.append(term.free_index_signature())

        first = signatures[0]
        for position, signature in enumerate(signatures[1:], start=2):
            if signature != first:
                raise ValueError(
                    "Tensor expression terms have incompatible free-index signatures: "
                    f"term 1={first}, term {position}={signature}."
                )
        return first

    @property
    def free_indices(self) -> List[TensorIndex]:
        self.validate_index_structure()
        return self.terms[0].free_indices

    @property
    def contracted_indices(self) -> List[str]:
        self.validate_index_structure()
        labels = set()
        for term in self.terms:
            labels.update(term.contracted_labels)
        return sorted(labels)

    def compatible_with(self, other: "TensorExpression") -> bool:
        """Return whether two tensor expressions can be equated structurally."""
        return self.validate_index_structure() == other.validate_index_structure()


def validate_tensor_equation(
    left: TensorExpression,
    right: TensorExpression,
) -> List[Tuple[str, str, Optional[int]]]:
    """Validate both sides and return their common free-index signature."""
    left_signature = left.validate_index_structure()
    right_signature = right.validate_index_structure()
    if left_signature != right_signature:
        raise ValueError(
            "Tensor equation has incompatible free-index signatures: "
            f"left={left_signature}, right={right_signature}."
        )
    return left_signature
