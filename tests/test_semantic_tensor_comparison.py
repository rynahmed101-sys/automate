"""Adversarial tests for the explicit semantic tensor subset."""

from automate.ir.tensors import TensorEquation, TensorExpression, TensorIndex, TensorProduct, TensorQuantity
from automate.tensors.semantic_comparison import (
    IndexSpace,
    SemanticResult,
    TensorSemanticContext,
    semantic_compare,
    validate_semantics,
)


def _eq(index_space="V", second_symbol="j", symmetry=None):
    i = TensorIndex(symbol="i", position="upper", dimension=4, index_space=index_space)
    j = TensorIndex(symbol=second_symbol, position="lower", dimension=4, index_space=index_space)
    t = TensorQuantity(name="T", indices=[i, j], symmetry=symmetry)
    p = TensorProduct(factors=[t])
    e = TensorExpression(terms=[[i, j]], products=[p])
    return TensorEquation(lhs=e, rhs=e.model_copy(deep=True))


def _ctx():
    return TensorSemanticContext(index_spaces=[IndexSpace(name="V", dimension=4)])


def test_renamed_dummy_index_is_supported_by_independent_path():
    i_upper = TensorIndex(symbol="i", position="upper", dimension=4, index_space="V")
    i_lower = TensorIndex(symbol="i", position="lower", dimension=4, index_space="V")
    a_upper = TensorIndex(symbol="a", position="upper", dimension=4, index_space="V")
    a_lower = TensorIndex(symbol="a", position="lower", dimension=4, index_space="V")
    left = TensorExpression(
        terms=[[i_upper, i_lower]],
        products=[TensorProduct(factors=[TensorQuantity(name="T", indices=[i_upper, i_lower])])],
    )
    right = TensorExpression(
        terms=[[a_upper, a_lower]],
        products=[TensorProduct(factors=[TensorQuantity(name="T", indices=[a_upper, a_lower])])],
    )
    result = semantic_compare(
        TensorEquation(lhs=left, rhs=left.model_copy(deep=True)),
        TensorEquation(lhs=right, rhs=right.model_copy(deep=True)),
        _ctx(),
    )
    assert result["result"] == SemanticResult.SEMANTIC_MATCH.value


def test_missing_index_space_fails_closed():
    equation = _eq()
    equation.lhs.products[0].factors[0].indices[0].index_space = None
    assert validate_semantics(equation, _ctx())


def test_same_dimension_different_index_spaces_do_not_match():
    left = _eq("V")
    right = _eq("W")
    ctx = TensorSemanticContext(index_spaces=[
        IndexSpace(name="V", dimension=4),
        IndexSpace(name="W", dimension=4),
    ])
    result = semantic_compare(left, right, ctx)
    assert result["result"] == SemanticResult.SEMANTIC_DISCREPANCY.value


def test_unsupported_symmetry_is_not_discrepancy():
    equation = _eq(symmetry="young_tableau")
    result = semantic_compare(equation, equation, _ctx())
    assert result["result"] == SemanticResult.UNSUPPORTED_SEMANTICS.value


def test_malformed_riemann_rank_fails_closed():
    equation = _eq(symmetry="riemann")
    assert validate_semantics(equation, _ctx())


def test_cross_space_contraction_fails_closed():
    i = TensorIndex(symbol="i", position="upper", dimension=4, index_space="V")
    j = TensorIndex(symbol="i", position="lower", dimension=4, index_space="W")
    left = TensorExpression(
        terms=[[i, j]],
        products=[TensorProduct(factors=[
            TensorQuantity(name="T", indices=[i]),
            TensorQuantity(name="S", indices=[j]),
        ])],
    )
    equation = TensorEquation(lhs=left, rhs=left.model_copy(deep=True))
    ctx = TensorSemanticContext(index_spaces=[
        IndexSpace(name="V", dimension=4),
        IndexSpace(name="W", dimension=4),
    ])
    assert validate_semantics(equation, ctx)
