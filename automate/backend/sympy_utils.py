"""
Restricted SymPy expression parsing for AI-generated mathematical input.

The verifier must parse mathematics as data, not execute arbitrary Python.  This
module gives SymPy an explicit allow-list of constructors and functions and
removes Python builtins from the parser global namespace.
"""

from typing import Any, Dict, Optional

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

_SAFE_GLOBALS: Dict[str, Any] = {
    "__builtins__": {},
    "Abs": sp.Abs,
    "Add": sp.Add,
    "Float": sp.Float,
    "Integer": sp.Integer,
    "Mul": sp.Mul,
    "Pow": sp.Pow,
    "Rational": sp.Rational,
    "Symbol": sp.Symbol,
    "Tuple": sp.Tuple,
    "pi": sp.pi,
    "E": sp.E,
    "I": sp.I,
    "oo": sp.oo,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
}


def safe_parse_expr(text: str, locals_map: Optional[Dict[str, Any]] = None) -> sp.Expr:
    """Parse a mathematical expression without exposing Python builtins."""
    if not isinstance(text, str):
        raise TypeError("Mathematical expression must be a string.")
    stripped = text.strip()
    if not stripped:
        raise ValueError("Mathematical expression cannot be empty.")

    return parse_expr(
        stripped,
        local_dict=dict(locals_map or {}),
        global_dict=_SAFE_GLOBALS,
        transformations=_TRANSFORMATIONS,
        evaluate=True,
    )
