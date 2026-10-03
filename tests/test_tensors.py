"""
Tests for canonical tensor semantics, Einstein summation, and index algebra.
"""

import pytest
from automate.ir.tensors import (
    TensorIndex,
    TensorQuantity,
    IndexValidationResult,
    validate_einstein_product,
    validate_tensor_sum,
    validate_tensor_equation,
)


def test_tensor_index_properties():
    idx1 = TensorIndex(symbol="mu", position="upper", is_dummy=False)
    idx2 = TensorIndex(symbol="mu", position="lower", is_dummy=True)

    assert idx1.symbol == "mu"
    assert idx1.position == "upper"
    assert idx1.variance == "contravariant"
    assert idx2.position == "lower"
    assert idx2.variance == "covariant"
    assert idx2.is_dummy is True


def test_einstein_product_contraction():
    # Ricci tensor R_{\mu \nu} (rank 2, both covariant / lower)
    r_indices = [
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ]
    ricci = TensorQuantity(name="R", indices=r_indices, symmetry="symmetric")
    assert ricci.rank == 2

    # Inverse metric g^{\mu \nu} (rank 2, both contravariant / upper)
    g_indices = [
        TensorIndex(symbol="mu", position="upper"),
        TensorIndex(symbol="nu", position="upper"),
    ]
    metric_inv = TensorQuantity(name="g_inv", indices=g_indices, symmetry="symmetric")
    assert metric_inv.rank == 2

    # Contraction R_{\mu \nu} g^{\mu \nu} -> Scalar R (rank 0)
    result = validate_einstein_product(ricci.indices + metric_inv.indices)
    assert result.is_valid is True
    assert result.resultant_rank == 0
    assert len(result.free_indices) == 0
    assert set(result.dummy_indices) == {"mu", "nu"}


def test_einstein_product_mixed_rank():
    # T^\mu_\nu (rank 2) * v^\nu (rank 1) -> vector w^\mu (rank 1)
    t = TensorQuantity(name="T", indices=[
        TensorIndex(symbol="mu", position="upper"),
        TensorIndex(symbol="nu", position="lower"),
    ])
    v = TensorQuantity(name="v", indices=[
        TensorIndex(symbol="nu", position="upper"),
    ])

    result = validate_einstein_product(t.indices + v.indices)
    assert result.is_valid is True
    assert result.resultant_rank == 1
    assert len(result.free_indices) == 1
    assert result.free_indices[0].symbol == "mu"
    assert result.free_indices[0].position == "upper"
    assert result.dummy_indices == ["nu"]


def test_einstein_product_invalid_same_variance_contraction():
    # R_{\mu \nu} * A_\mu (illegal: \mu appears twice as lower indices)
    r = TensorQuantity(name="R", indices=[
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ])
    a = TensorQuantity(name="A", indices=[
        TensorIndex(symbol="mu", position="lower"),
    ])

    result = validate_einstein_product(r.indices + a.indices)
    assert result.is_valid is False
    assert any("both occurrences are in 'lower' position" in e for e in result.errors)


def test_einstein_product_illegal_triple_index():
    # \mu appears 3 times
    t1 = TensorQuantity(name="A", indices=[TensorIndex(symbol="mu", position="upper")])
    t2 = TensorQuantity(name="B", indices=[TensorIndex(symbol="mu", position="lower")])
    t3 = TensorQuantity(name="C", indices=[TensorIndex(symbol="mu", position="upper")])

    result = validate_einstein_product(t1.indices + t2.indices + t3.indices)
    assert result.is_valid is False
    assert any("appears 3 times" in e for e in result.errors)


def test_tensor_sum_valid_and_invalid():
    # Both rank 2 with free indices mu, nu (lower)
    t1 = TensorQuantity(name="R", indices=[
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ])
    t2 = TensorQuantity(name="T", indices=[
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ])

    sum_res = validate_tensor_sum([t1.indices, t2.indices])
    assert sum_res.is_valid is True
    assert sum_res.resultant_rank == 2

    # Mismatched rank: rank 2 + rank 1
    v = TensorQuantity(name="v", indices=[
        TensorIndex(symbol="mu", position="lower"),
    ])
    sum_bad_rank = validate_tensor_sum([t1.indices, v.indices])
    assert sum_bad_rank.is_valid is False
    assert any("Free index mismatch" in e for e in sum_bad_rank.errors)

    # Mismatched index position: (lower, lower) + (upper, lower)
    t3 = TensorQuantity(name="T_mixed", indices=[
        TensorIndex(symbol="mu", position="upper"),
        TensorIndex(symbol="nu", position="lower"),
    ])
    sum_bad_pos = validate_tensor_sum([t1.indices, t3.indices])
    assert sum_bad_pos.is_valid is False
    assert any("Free index mismatch" in e for e in sum_bad_pos.errors)


def test_tensor_equation_validation():
    # Einstein field equation: G_{\mu \nu} = 8 \pi G T_{\mu \nu}
    g_munu = TensorQuantity(name="G", indices=[
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ])
    t_munu = TensorQuantity(name="T", indices=[
        TensorIndex(symbol="mu", position="lower"),
        TensorIndex(symbol="nu", position="lower"),
    ])

    eq_res = validate_tensor_equation(g_munu.indices, t_munu.indices)
    assert eq_res.is_valid is True
    assert eq_res.resultant_rank == 2

    # Invalid: LHS rank 2, RHS rank 1
    t_mu = TensorQuantity(name="T_vec", indices=[
        TensorIndex(symbol="mu", position="lower"),
    ])

    eq_bad = validate_tensor_equation(g_munu.indices, t_mu.indices)
    assert eq_bad.is_valid is False
    assert any("Equation index mismatch between LHS and RHS" in e for e in eq_bad.errors)
