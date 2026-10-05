"""Compatibility wrapper for the canonical SymPy-to-Lean arithmetic translator.

The implementation lives in graph_to_lean.py so graph-bound and legacy callers
share exactly the same arithmetic semantics and limits.
"""

import sympy as sp

from automate.backend.graph_to_lean import (
    GraphToLeanTranslationError as LeanExpressionTranslationError,
    translate_integer_expression,
)


def translate_integer_polynomial(expr: sp.Basic) -> tuple[str, list[str]]:
    """Backward-compatible name for the canonical integer expression translator."""
    return translate_integer_expression(expr)


def translate_identity(lhs: sp.Basic, rhs: sp.Basic) -> tuple[str, list[str]]:
    """Translate an integer-polynomial equality into a Lean proposition."""
    lhs_code, lhs_names = translate_integer_expression(lhs)
    rhs_code, rhs_names = translate_integer_expression(rhs)
    names = sorted(set(lhs_names).union(rhs_names))
    proposition = f"({lhs_code} : Int) = ({rhs_code} : Int)"
    return proposition, names
