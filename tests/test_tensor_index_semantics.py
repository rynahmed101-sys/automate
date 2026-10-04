"""Adversarial tests for structured Einstein-index semantics."""

import pytest

from automate.tensors.index import (
    TensorExpression,
    TensorFactor,
    TensorIndex,
    TensorSymbol,
    TensorTerm,
    validate_tensor_equation,
)


def _factor(name, variance, labels, dimensions=None):
    symbol = TensorSymbol(
        name=name,
        variance=variance,
        dimensions=dimensions or [],
    )
    return TensorFactor(
        tensor=symbol,
        indices=[
            TensorIndex(label=label, variance=slot_variance, dimension=dimension)
            for slot_variance, label, dimension in zip(
                variance,
                labels,
                dimensions or [None] * len(labels),
            )
        ],
    )


def test_tensor_factor_requires_rank_and_variance_match():
    with pytest.raises(ValueError, match="rank"):
        TensorFactor(
            tensor=TensorSymbol(name="g", variance=["down", "down"]),
            indices=[TensorIndex(label="mu", variance="down")],
        )

    with pytest.raises(ValueError, match="expects up variance"):
        TensorFactor(
            tensor=TensorSymbol(name="v", variance=["up"]),
            indices=[TensorIndex(label="mu", variance="down")],
        )


def test_valid_einstein_contraction_is_accepted():
    term = TensorTerm(
        factors=[
            _factor("A", ["up", "down"], ["mu", "nu"]),
            _factor("B", ["up"], ["nu"]),
        ]
    )

    term.validate_einstein_summation()
    assert term.contracted_labels == ["nu"]
    assert term.free_index_signature() == [("mu", "up", None)]


def test_repeated_index_must_have_opposite_variance():
    term = TensorTerm(
        factors=[
            _factor("A", ["up"], ["mu"]),
            _factor("B", ["up"], ["mu"]),
        ]
    )

    with pytest.raises(ValueError, match="once up and once down"):
        term.validate_einstein_summation()


def test_index_cannot_occur_more_than_twice_in_one_term():
    term = TensorTerm(
        factors=[
            _factor("A", ["up"], ["mu"]),
            _factor("B", ["down"], ["mu"]),
            _factor("C", ["up"], ["mu"]),
        ]
    )

    with pytest.raises(ValueError, match="occurs 3 times"):
        term.validate_einstein_summation()


def test_contracted_index_dimension_must_agree():
    term = TensorTerm(
        factors=[
            _factor("A", ["up"], ["mu"], [4]),
            _factor("B", ["down"], ["mu"], [3]),
        ]
    )

    with pytest.raises(ValueError, match="incompatible dimensions"):
        term.validate_einstein_summation()


def test_sum_terms_must_share_free_index_signature():
    expression = TensorExpression(
        terms=[
            TensorTerm(factors=[_factor("A", ["up", "down"], ["mu", "nu"])]),
            TensorTerm(factors=[_factor("B", ["up", "down"], ["mu", "rho"])]),
        ]
    )

    with pytest.raises(ValueError, match="free-index signatures"):
        expression.validate_index_structure()


def test_tensor_equation_requires_matching_free_indices():
    left = TensorExpression(
        terms=[
            TensorTerm(
                factors=[
                    _factor("A", ["up", "down"], ["mu", "nu"]),
                    _factor("B", ["up"], ["nu"]),
                ]
            )
        ]
    )
    right = TensorExpression(
        terms=[
            TensorTerm(
                factors=[
                    _factor("C", ["up"], ["rho"]),
                ]
            )
        ]
    )

    with pytest.raises(ValueError, match="incompatible free-index signatures"):
        validate_tensor_equation(left, right)


def test_tensor_equation_accepts_matching_free_indices():
    left = TensorExpression(
        terms=[
            TensorTerm(
                factors=[
                    _factor("A", ["up", "down"], ["mu", "nu"]),
                    _factor("B", ["up"], ["nu"]),
                ]
            )
        ]
    )
    right = TensorExpression(
        terms=[
            TensorTerm(
                factors=[
                    _factor("C", ["up", "down"], ["mu", "nu"]),
                    _factor("D", ["up"], ["nu"]),
                ]
            )
        ]
    )

    signature = validate_tensor_equation(left, right)
    assert signature == [("mu", "up", None)]


def test_structured_tensor_ir_roundtrips():
    expression = TensorExpression(
        terms=[
            TensorTerm(
                factors=[
                    _factor("g", ["down", "down"], ["mu", "nu"], [4, 4]),
                    _factor("v", ["up"], ["nu"], [4]),
                ]
            )
        ]
    )

    restored = TensorExpression.model_validate(expression.model_dump())
    assert restored.model_dump() == expression.model_dump()
