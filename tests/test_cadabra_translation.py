"""Tests for canonical Tensor IR -> Cadabra translation."""

import pytest

from automate.ir.tensors import TensorExpression, TensorIndex, TensorProduct, TensorQuantity
from automate.tensors.cadabra_translation import (
    tensor_expression_to_cadabra,
    translate_expression,
)


def _idx(symbol, position="lower", dimension=4):
    return TensorIndex(symbol=symbol, position=position, dimension=dimension)


def test_translates_named_tensor_product():
    expression = TensorExpression(
        terms=[[ _idx("a", "lower"), _idx("b", "upper"), _idx("b", "lower") ]],
        products=[
            TensorProduct(factors=[
                TensorQuantity(name="R", indices=[_idx("a", "lower"), _idx("b", "upper")]),
                TensorQuantity(name="v", indices=[_idx("b", "lower")]),
            ])
        ],
    )
    source = tensor_expression_to_cadabra(expression)
    assert source == "R_{a}^{b} v_{b}"


def test_rejects_legacy_index_only_expression():
    expression = TensorExpression(
        terms=[[_idx("a")]],
    )
    with pytest.raises(ValueError, match="factor names"):
        tensor_expression_to_cadabra(expression)


def test_rejects_invalid_identifier():
    expression = TensorExpression(
        terms=[[_idx("a")]],
        products=[
            TensorProduct(factors=[
                TensorQuantity(name="bad-name", indices=[_idx("a")]),
            ])
        ],
    )
    with pytest.raises(ValueError, match="identifier"):
        tensor_expression_to_cadabra(expression)


def test_rejects_invalid_contraction_before_translation():
    expression = TensorExpression(
        terms=[[_idx("a", "lower"), _idx("a", "lower")]],
        products=[
            TensorProduct(factors=[
                TensorQuantity(name="R", indices=[_idx("a", "lower"), _idx("a", "lower")]),
            ])
        ],
    )
    with pytest.raises(ValueError, match="Einstein summation"):
        tensor_expression_to_cadabra(expression)


def test_translation_fingerprint_changes_with_ir():
    one = TensorExpression(
        terms=[[_idx("a")]],
        products=[TensorProduct(factors=[TensorQuantity(name="A", indices=[_idx("a")])])],
    )
    two = TensorExpression(
        terms=[[_idx("a")]],
        products=[TensorProduct(factors=[TensorQuantity(name="B", indices=[_idx("a")])])],
    )
    assert translate_expression(one)["ir_fingerprint_sha256"] != translate_expression(two)["ir_fingerprint_sha256"]
