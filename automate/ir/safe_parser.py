"""
safe_parser.py — Restricted mathematical expression parser for Automate.

This module is the SOLE security boundary between untrusted mathematical
strings (from user input or AI proposals) and the SymPy evaluation engine.

Security properties:
  - Explicit allowlist of mathematical functions only.
  - All Python builtins disabled in sympify locals.
  - Attribute traversal (__dunder__, getattr, type) blocked at string level.
  - Expression size (atom count) and depth limited.
  - Arbitrary constructor/class calls blocked.
  - No eval(), exec(), import, open, os, sys, subprocess.
  - Rejects strings that match injection patterns before parsing.

Usage:
    from automate.ir.safe_parser import SafeParser

    parser = SafeParser()
    expr = parser.parse("m * x_ddot + k * x")      # returns sp.Expr
    expr = parser.parse("A * cos(omega * t + phi)") # returns sp.Expr
    expr = parser.parse("__import__('os')")          # raises SafeParseError
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional, Set

import sympy as sp
from sympy import (
    Symbol, Function, Integer, Rational, Float,
    pi, E, I, oo, nan, zoo,
    sin, cos, tan, asin, acos, atan, atan2,
    sinh, cosh, tanh, asinh, acosh, atanh,
    sqrt, exp, log, ln, Abs, sign,
    re as sp_re, im as sp_im, conjugate,
    diff, Derivative, Integral,
)


# ---------------------------------------------------------------------------
# Error class
# ---------------------------------------------------------------------------

class SafeParseError(ValueError):
    """Raised when a mathematical expression cannot be safely parsed."""
    pass


# ---------------------------------------------------------------------------
# Injection patterns blocked before any SymPy call
# ---------------------------------------------------------------------------

_BLOCK_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"__\w+__",             # dunder attributes (__import__, __class__, etc.)
    r"\bimport\b",          # import statement
    r"\beval\s*\(",         # eval() call
    r"\bexec\s*\(",         # exec() call
    r"\bopen\s*\(",         # file open
    r"\bgetattr\s*\(",      # attribute traversal
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
    r"\bhasattr\s*\(",
    r"\btype\s*\(",         # type() for arbitrary class construction
    r"\bcompile\s*\(",
    r"\bglobals\s*\(",
    r"\blocals\s*\(",
    r"\bvars\s*\(",
    r"\bdir\s*\(",
    r"\bsubprocess\b",
    r"\bos\s*\.\s*\w+",
    r"\bsys\s*\.\s*\w+",
    r"\bshutil\b",
    r"\bpathlib\b",
    r"\bsocket\b",
    r"\burllib\b",
    r"\brequests\b",
    r"\bpickle\b",
    r"\bmarshall\b",
    r"\bbuiltins\b",
    r"\bchr\s*\(",
    r"\bord\s*\(",
    r"\bhex\s*\(",
    r"\boct\s*\(",
    r"\bbin\s*\(",
    r"\bformat\s*\(",
    r"\brepr\s*\(",
    r"\bprint\s*\(",        # avoid information leakage
    r"\binput\s*\(",
    r"lambda\s+",           # anonymous functions
    r":\s*=",               # walrus operator
    r"yield\b",
    r"async\b",
    r"await\b",
    r"\.\.+",               # path traversal
    r";.*",                 # statement separator
]]

# ---------------------------------------------------------------------------
# Allowed functions allowlist
# ---------------------------------------------------------------------------

_ALLOWED_FUNCTIONS: Dict[str, Any] = {
    # Trigonometric
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan, "atan2": atan2,
    "arcsin": asin, "arccos": acos, "arctan": atan,
    # Hyperbolic
    "sinh": sinh, "cosh": cosh, "tanh": tanh,
    "asinh": asinh, "acosh": acosh, "atanh": atanh,
    # Exponential / logarithm
    "exp": exp, "log": log, "ln": log, "sqrt": sqrt,
    "log2": lambda x: log(x, 2), "log10": lambda x: log(x, 10),
    # Absolute value / sign
    "Abs": Abs, "abs": Abs, "sign": sign,
    # Complex
    "re": sp_re, "im": sp_im, "conjugate": conjugate,
    # Calculus
    "diff": diff, "Derivative": Derivative, "Integral": Integral,
    # Constants
    "pi": pi, "E": E, "I": I, "oo": oo, "nan": nan, "zoo": zoo,
    # Common physics symbols as plain Symbols (not reserved)
    # Note: gamma, alpha, beta etc. are plain symbols in physics
    # They are NOT added here to avoid overriding user-defined symbols.
    # Constructors allowed only for scalars/symbols
    "Symbol": Symbol, "Integer": Integer, "Rational": Rational, "Float": Float,
    # SymPy Function base (so x(t) notation works)
    "Function": Function,
}


# Max atom count in a parsed expression (DoS prevention)
_MAX_ATOM_COUNT = 2000
# Max recursion depth in SymPy expression tree
_MAX_DEPTH = 80
# Max parse time in seconds
_MAX_PARSE_SECONDS = 10.0
# Max raw string length (chars)
_MAX_STRING_LENGTH = 4096


# ---------------------------------------------------------------------------
# Depth measurement
# ---------------------------------------------------------------------------

def _expression_depth(expr: sp.Basic, _memo: Optional[Dict[int, int]] = None) -> int:
    """Recursively computes the depth of a SymPy expression tree."""
    if _memo is None:
        _memo = {}
    eid = id(expr)
    if eid in _memo:
        return _memo[eid]
    if not expr.args:
        _memo[eid] = 1
        return 1
    depth = 1 + max(_expression_depth(arg, _memo) for arg in expr.args)
    _memo[eid] = depth
    return depth


# ---------------------------------------------------------------------------
# SafeParser
# ---------------------------------------------------------------------------

class SafeParser:
    """
    Restricted expression parser. Converts a mathematical string into a
    SymPy expression using an explicit function allowlist and injection
    blocking patterns.

    Parameters
    ----------
    extra_symbols : dict, optional
        Additional safe Symbol bindings to add to the locals dict
        (e.g. coordinate functions, parameter symbols).
    max_atoms : int
        Maximum number of atoms (leaves) in the parsed expression.
    max_depth : int
        Maximum expression tree depth.
    max_seconds : float
        Maximum wall-clock time for a single parse call.
    """

    def __init__(
        self,
        extra_symbols: Optional[Dict[str, Any]] = None,
        max_atoms: int = _MAX_ATOM_COUNT,
        max_depth: int = _MAX_DEPTH,
        max_seconds: float = _MAX_PARSE_SECONDS,
    ):
        self.max_atoms = max_atoms
        self.max_depth = max_depth
        self.max_seconds = max_seconds
        self._base_locals: Dict[str, Any] = dict(_ALLOWED_FUNCTIONS)
        if extra_symbols:
            import types as _types
            # Validate that extra_symbols values are safe SymPy objects or symbols
            for k, v in extra_symbols.items():
                if not isinstance(k, str) or not k.replace("_", "").isalnum():
                    raise SafeParseError(
                        f"extra_symbols key '{k}' is not a valid identifier."
                    )
                # Reject Python modules, arbitrary classes not derived from SymPy
                if isinstance(v, _types.ModuleType):
                    raise SafeParseError(
                        f"extra_symbols value for '{k}' is a Python module, "
                        "which is not allowed."
                    )
                if isinstance(v, type) and not (
                    issubclass(v, sp.Basic) or issubclass(v, sp.core.function.UndefinedFunction)
                ):
                    raise SafeParseError(
                        f"extra_symbols value for '{k}' is not a SymPy type."
                    )
            self._base_locals.update(extra_symbols)


    def _check_string(self, s: str) -> None:
        """Pre-parse string-level security checks."""
        if len(s) > _MAX_STRING_LENGTH:
            raise SafeParseError(
                f"Expression string too long: {len(s)} chars "
                f"(max {_MAX_STRING_LENGTH})."
            )
        for pat in _BLOCK_PATTERNS:
            m = pat.search(s)
            if m:
                raise SafeParseError(
                    f"Expression contains disallowed pattern '{pat.pattern}' "
                    f"at position {m.start()}: {m.group()!r}"
                )

    def _check_expr(self, expr: sp.Basic) -> None:
        """Post-parse expression-level checks."""
        atom_count = len(expr.atoms())
        if atom_count > self.max_atoms:
            raise SafeParseError(
                f"Parsed expression has {atom_count} atoms "
                f"(max {self.max_atoms}). Possible DoS payload."
            )
        depth = _expression_depth(expr)
        if depth > self.max_depth:
            raise SafeParseError(
                f"Parsed expression depth is {depth} "
                f"(max {self.max_depth}). Possible DoS payload."
            )
        # Reject any Symbol whose name looks like an injection attempt
        for sym in expr.free_symbols:
            name = str(sym)
            if "__" in name or re.search(r"[^a-zA-Z0-9_]", name):
                raise SafeParseError(
                    f"Symbol name '{name}' contains disallowed characters."
                )

    def parse(
        self,
        expr_str: str,
        extra_locals: Optional[Dict[str, Any]] = None,
    ) -> sp.Expr:
        """
        Parse a mathematical expression string into a SymPy expression.

        Parameters
        ----------
        expr_str : str
            The mathematical expression string to parse.
        extra_locals : dict, optional
            Additional safe locals (coordinate functions, etc.) for this parse call.

        Returns
        -------
        sp.Expr
            The parsed SymPy expression.

        Raises
        ------
        SafeParseError
            If the string fails any security check or limits.
        """
        if not isinstance(expr_str, str):
            raise SafeParseError(
                f"Expression must be a string, got {type(expr_str).__name__}."
            )

        s = expr_str.strip()
        if not s:
            raise SafeParseError("Empty expression string.")

        # Pre-parse security checks
        self._check_string(s)

        # Build safe locals dict (no Python builtins)
        safe_locals: Dict[str, Any] = dict(self._base_locals)
        if extra_locals:
            # Validate extra_locals keys
            for k in extra_locals:
                if not isinstance(k, str):
                    raise SafeParseError(
                        f"extra_locals key must be a string, got {type(k).__name__}."
                    )
            safe_locals.update(extra_locals)

        # Parse with timeout check
        t0 = time.monotonic()
        try:
            # transformations=[] disables auto-Symbol creation which could
            # allow arbitrary attribute names to become symbols
            expr = sp.sympify(s, locals=safe_locals, evaluate=True)
        except (sp.SympifyError, TypeError, AttributeError, ValueError) as exc:
            raise SafeParseError(
                f"SymPy failed to parse expression: {exc}"
            ) from exc
        except Exception as exc:
            raise SafeParseError(
                f"Unexpected parse error: {type(exc).__name__}: {exc}"
            ) from exc

        elapsed = time.monotonic() - t0
        if elapsed > self.max_seconds:
            raise SafeParseError(
                f"Parse exceeded time limit of {self.max_seconds}s "
                f"(took {elapsed:.2f}s)."
            )

        # Post-parse expression checks
        self._check_expr(expr)

        return expr

    def parse_equation(
        self,
        eq_str: str,
        extra_locals: Optional[Dict[str, Any]] = None,
    ) -> sp.Expr:
        """
        Parse a mathematical equation of the form 'LHS = RHS' or bare 'LHS'.
        Returns LHS - RHS as a single expression.

        Raises
        ------
        SafeParseError
            On security, limit, or format violations.
        """
        s = eq_str.strip()
        self._check_string(s)

        if "=" in s:
            # Split on first = only; do NOT use = as equality token naively
            # Reject == if it appears (Python equality, not math)
            if "==" in s:
                raise SafeParseError(
                    "Double == in equation string. Use single = for math equality."
                )
            lhs_str, rhs_str = s.split("=", 1)
            lhs = self.parse(lhs_str.strip(), extra_locals)
            rhs = self.parse(rhs_str.strip(), extra_locals)
            return sp.nsimplify(lhs - rhs, rational=False)
        else:
            return self.parse(s, extra_locals)

    def make_symbol(self, name: str, **assumptions: Any) -> sp.Symbol:
        """
        Create a SymPy Symbol after validating the name.
        Only alphanumeric + underscore names starting with a letter are allowed.
        """
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
            raise SafeParseError(
                f"Symbol name '{name}' is not a valid identifier. "
                "Must start with a letter and contain only alphanumeric characters and underscores."
            )
        return sp.Symbol(name, **assumptions)

    def make_function(self, name: str) -> type:
        """
        Create a SymPy Function class after validating the name.
        """
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
            raise SafeParseError(
                f"Function name '{name}' is not a valid identifier."
            )
        return sp.Function(name)
