"""Adversarial tests for the canonical structured tensor IR."""

import pytest

from automate.ir.tensors import (
    TensorEquation,
    TensorExpression,
    TensorIndex,
    TensorQuantity,
    validate_einstein_product,
)


def idx(symbol, position, dimension=None):
    return TensorIndex(
        symbol=symbol,
        position=position,
        dimension=dimension,
    )


def test_valid_einstein_contraction_is_accepted():
    result = validate_einstein_product([
        idx("mu", "lower"),
        idx("nu", "upper"),
        idx("nu", "lower"),
    ])

    assert result.is_valid is True
    assert result.resultant_rank == 1
    assert result.free_indices[0].symbol == "mu"
    assert result.dummy_indices == ["nu"]


def test_repeated_index_must_have_opposite_variance():
    result = validate_einstein_product([
        idx("mu", "upper"),
        idx("mu", "upper"),
    ])

    assert result.is_valid is False
    assert any("both occurrences are in 'upper'" in error for error in result.errors)


def test_index_cannot_occur_more_than_twice_in_one_term():
    result = validate_einstein_product([
        idx("mu", "upper"),
        idx("mu", "lower"),
        idx("mu", "upper"),
    ])

    assert result.is_valid is False
    assert any("appears 3 times" in error for error in result.errors)


def test_contracted_index_dimension_must_agree():
    result = validate_einstein_product([
        idx("mu", "upper", 4),
        idx("mu", "lower", 3),
    ])

    assert result.is_valid is False
    assert any("incompatible index dimensions" in error for error in result.errors)


def test_tensor_sum_requires_matching_free_index_signature():
    expression = TensorExpression(
        terms=[
            [
                idx("mu", "lower"),
                idx("nu", "lower"),
            ],
            [
                idx("mu", "lower"),
                idx("rho", "lower"),
            ],
        ]
    )

    result = expression.validate_structure()
    assert result.is_valid is False
    assert any("Free index mismatch" in error for error in result.errors)


def test_tensor_equation_requires_matching_free_indices():
    equation = TensorEquation(
        lhs=TensorExpression(
            terms=[[idx("mu", "lower"), idx("nu", "lower")]]
        ),
        rhs=TensorExpression(
            terms=[[idx("mu", "lower")]]
        ),
    )

    result = equation.validate_structure()
    assert result.is_valid is False
    assert any("Equation index mismatch" in error for error in result.errors)


def test_tensor_equation_accepts_matching_free_indices():
    equation = TensorEquation(
        lhs=TensorExpression(
            terms=[[idx("mu", "lower"), idx("nu", "lower")]]
        ),
        rhs=TensorExpression(
            terms=[[idx("mu", "lower"), idx("nu", "lower")]]
        ),
    )

    result = equation.validate_structure()
    assert result.is_valid is True
    assert equation.free_index_signature == [
        ("mu", "lower"),
        ("nu", "lower"),
    ]


def test_tensor_quantity_rank_is_explicitly_structured():
    quantity = TensorQuantity(
        name="G",
        indices=[
            idx("mu", "lower"),
            idx("nu", "lower"),
        ],
        symmetry="symmetric",
    )

    assert quantity.rank == 2
    assert quantity.free_indices[0].symbol == "mu"


def test_structured_tensor_ir_roundtrips():
    expression = TensorExpression(
        terms=[[
            idx("mu", "lower", 4),
            idx("nu", "lower", 4),
        ]]
    )

    restored = TensorExpression.model_validate(expression.model_dump())
    assert restored.model_dump() == expression.model_dump()


def test_tensor_expression_free_signature_rejects_invalid_structure():
    expression = TensorExpression(
        terms=[[
            idx("mu", "lower"),
            idx("mu", "lower"),
        ]]
    )

    with pytest.raises(ValueError):
        _ = expression.free_index_signature
