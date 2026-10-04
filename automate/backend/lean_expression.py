"""
Restricted SymPy-to-Lean expression translation for algebraic identities.

This module is intentionally small and conservative. It translates only integer
polynomial expressions into Lean Int expressions. Unsupported constructs return
an explicit reason rather than guessing a representation or silently changing
semantics.
"""

import re

import sympy as sp


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_\']*$")
_MAX_NODES = 80
_MAX_POWER = 8


class LeanExpressionTranslationError(ValueError):
    pass


def _check_identifier(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise LeanExpressionTranslationError(
            f"Unsupported symbol name for Lean binding: {name!r}"
        )
    if name in {
        "theorem", "example", "def", "let", "fun", "match", "where", "if",
        "then", "else", "namespace", "end", "import", "open", "variable",
    }:
        raise LeanExpressionTranslationError(
            f"Lean keyword cannot be used as a symbol: {name!r}"
        )
    return name


def _count_nodes(expr: sp.Basic) -> int:
    count = sum(1 for _ in sp.preorder_traversal(expr))
    if count > _MAX_NODES:
        raise LeanExpressionTranslationError(
            f"Expression exceeds translation node budget ({_MAX_NODES})."
        )
    return count


def _translate(expr: sp.Basic) -> str:
    if isinstance(expr, sp.Integer):
        return str(int(expr))

    if isinstance(expr, sp.Symbol):
        return _check_identifier(expr.name)

    if isinstance(expr, sp.Add):
        terms = [_translate(arg) for arg in expr.args]
        if not terms:
            return "0"
        return "(" + " + ".join(terms) + ")"

    if isinstance(expr, sp.Mul):
        factors = list(expr.args)
        if not factors:
            return "1"
        pieces = [_translate(arg) for arg in factors]
        return "(" + " * ".join(pieces) + ")"

    if isinstance(expr, sp.Pow):
        base, exponent = expr.args
        if not isinstance(exponent, sp.Integer):
            raise LeanExpressionTranslationError(
                "Only integer powers are supported."
            )
        exponent_int = int(exponent)
        if exponent_int < 0 or exponent_int > _MAX_POWER:
            raise LeanExpressionTranslationError(
                f"Power {exponent_int} is outside supported range 0..{_MAX_POWER}."
            )
        return f"({_translate(base)} ^ {exponent_int})"

    raise LeanExpressionTranslationError(
        f"Unsupported SymPy node for Lean translation: {type(expr).__name__}"
    )


def translate_integer_polynomial(expr: sp.Basic) -> tuple[str, list[str]]:
    _count_nodes(expr)

    for atom in expr.atoms(sp.Rational):
        if type(atom) is sp.Rational and atom.q != 1:
            raise LeanExpressionTranslationError(
                "Non-integer rational coefficients are not supported."
            )

    names = sorted(
        _check_identifier(symbol.name)
        for symbol in expr.free_symbols
    )
    return _translate(expr), names


def translate_identity(lhs: sp.Basic, rhs: sp.Basic) -> tuple[str, list[str]]:
    """Translate both sides independently and merge their free-symbol binders."""
    lhs_code, lhs_names = translate_integer_polynomial(lhs)
    rhs_code, rhs_names = translate_integer_polynomial(rhs)
    names = sorted(set(lhs_names).union(rhs_names))
    proposition = f"({lhs_code} : Int) = ({rhs_code} : Int)"
    return proposition, names
