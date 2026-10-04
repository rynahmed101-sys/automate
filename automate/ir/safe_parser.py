"""Restricted mathematical expression parser for Automate.

This module is the security boundary between untrusted mathematical strings
and SymPy objects.

Unlike sympy.sympify / parse_expr, the parser never evaluates the untrusted
source string as Python. Python's ast module is used only to parse syntax in
eval mode, then a small allowlisted AST is translated directly into SymPy
objects.

Security properties:
  - No eval(), exec(), sympify(), or parse_expr() is used on untrusted text.
  - Only arithmetic, numeric literals, names, tuples, and allowlisted calls
    are accepted.
  - Attribute access, subscripting, comprehensions, lambdas, assignments,
    imports, boolean/control-flow expressions, and arbitrary call targets are
    rejected structurally.
  - Additional bindings must be SymPy objects, SymPy undefined-function
    classes, or one of the parser's own allowlisted functions.
  - Expression size and AST depth are bounded before conversion.
  - Resulting SymPy expressions are checked for atom count, depth, and safe
    symbol/function names.

The parser deliberately accepts the project's existing mathematical notation
such as m * x_ddot + k * x, Rational(1,2) * x**2 and
diff(x(t), t, 2) when x is supplied as a safe SymPy function binding.
"""

from __future__ import annotations

import ast
import operator
import re
import time
from typing import Any, Callable, Dict, Optional

import sympy as sp
from sympy import (
    Symbol, Integer, Rational, Float,
    pi, E, I, oo, nan, zoo,
    sin, cos, tan, asin, acos, atan, atan2,
    sinh, cosh, tanh, asinh, acosh, atanh,
    sqrt, exp, log, ln, Abs, sign,
    re as sp_re, im as sp_im, conjugate,
    diff, Derivative, Integral,
)


class SafeParseError(ValueError):
    """Raised when a mathematical expression cannot be safely parsed."""
    pass


_BLOCK_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"__\w+__",
    r"\bimport\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bopen\s*\(",
    r"\bgetattr\s*\(",
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
    r"\bhasattr\s*\(",
    r"\btype\s*\(",
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
    r"\bprint\s*\(",
    r"\binput\s*\(",
    r"lambda\s+",
    r":\s*=",
    r"yield\b",
    r"async\b",
    r"await\b",
    r"\.\.+",
    r";.*",
]]

_ALLOWED_FUNCTIONS: Dict[str, Any] = {
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan, "atan2": atan2,
    "arcsin": asin, "arccos": acos, "arctan": atan,
    "sinh": sinh, "cosh": cosh, "tanh": tanh,
    "asinh": asinh, "acosh": acosh, "atanh": atanh,
    "exp": exp, "log": log, "ln": log, "sqrt": sqrt,
    "log2": lambda x: log(x, 2), "log10": lambda x: log(x, 10),
    "Abs": Abs, "abs": Abs, "sign": sign,
    "re": sp_re, "im": sp_im, "conjugate": conjugate,
    "diff": diff, "Derivative": Derivative, "Integral": Integral,
    "pi": pi, "E": E, "I": I, "oo": oo, "nan": nan, "zoo": zoo,
    "Symbol": Symbol, "Integer": Integer, "Rational": Rational, "Float": Float,
}

_MAX_ATOM_COUNT = 2000
_MAX_DEPTH = 80
_MAX_AST_NODES = 4000
_MAX_PARSE_SECONDS = 10.0
_MAX_STRING_LENGTH = 4096

_SAFE_BINARY_OPS: Dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_SAFE_UNARY_OPS: Dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _expression_depth(expr: sp.Basic, _memo: Optional[Dict[int, int]] = None) -> int:
    """Recursively compute the depth of a SymPy expression tree."""
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


def _ast_stats(tree: ast.AST) -> tuple[int, int]:
    nodes = list(ast.walk(tree))
    depth_cache: Dict[int, int] = {}

    def depth(node: ast.AST) -> int:
        nid = id(node)
        if nid in depth_cache:
            return depth_cache[nid]
        children = list(ast.iter_child_nodes(node))
        value = 1 + max((depth(child) for child in children), default=0)
        depth_cache[nid] = value
        return value

    return len(nodes), depth(tree)


def _is_safe_binding(value: Any) -> bool:
    if isinstance(value, sp.Basic):
        return True
    if isinstance(value, type):
        try:
            return issubclass(value, sp.core.function.UndefinedFunction)
        except TypeError:
            return False
    return any(value is allowed for allowed in _ALLOWED_FUNCTIONS.values())


class SafeParser:
    """Translate a restricted mathematical AST directly into SymPy."""

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
            self._validate_bindings(extra_symbols, "extra_symbols")
            self._base_locals.update(extra_symbols)

    @staticmethod
    def _validate_bindings(bindings: Dict[str, Any], label: str) -> None:
        if not isinstance(bindings, dict):
            raise SafeParseError(f"{label} must be a dictionary.")
        for key, value in bindings.items():
            if not isinstance(key, str) or not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", key):
                raise SafeParseError(
                    f"{label} key '{key}' is not a valid identifier."
                )
            if not _is_safe_binding(value):
                raise SafeParseError(
                    f"{label} value for '{key}' is not a permitted SymPy binding."
                )

    def _check_string(self, s: str) -> None:
        if len(s) > _MAX_STRING_LENGTH:
            raise SafeParseError(
                f"Expression string too long: {len(s)} chars "
                f"(max {_MAX_STRING_LENGTH})."
            )
        for pat in _BLOCK_PATTERNS:
            match = pat.search(s)
            if match:
                raise SafeParseError(
                    f"Expression contains disallowed pattern '{pat.pattern}' "
                    f"at position {match.start()}: {match.group()!r}"
                )

    def _check_expr(self, expr: sp.Basic) -> None:
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
        for sym in expr.free_symbols:
            name = str(sym)
            if "__" in name or not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
                raise SafeParseError(
                    f"Symbol name '{name}' contains disallowed characters."
                )
        for func in expr.atoms(sp.Function):
            name = str(getattr(func.func, "__name__", func.func))
            if "__" in name or not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
                raise SafeParseError(
                    f"Function name '{name}' contains disallowed characters."
                )

    def _convert(self, node: ast.AST, safe_locals: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float, complex)):
                raise SafeParseError("Only numeric literals are permitted in expressions.")
            if isinstance(node.value, int):
                return sp.Integer(node.value)
            if isinstance(node.value, float):
                return sp.Float(node.value)
            return sp.Float(node.value.real) + sp.I * sp.Float(node.value.imag)

        if isinstance(node, ast.Name):
            if node.id in safe_locals:
                return safe_locals[node.id]
            if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", node.id):
                raise SafeParseError(f"Invalid symbol name '{node.id}'.")
            return sp.Symbol(node.id)

        if isinstance(node, ast.Tuple):
            return tuple(self._convert(elt, safe_locals) for elt in node.elts)

        if isinstance(node, ast.UnaryOp):
            op = _SAFE_UNARY_OPS.get(type(node.op))
            if op is None:
                raise SafeParseError(f"Unary operator '{type(node.op).__name__}' is not permitted.")
            return op(self._convert(node.operand, safe_locals))

        if isinstance(node, ast.BinOp):
            op = _SAFE_BINARY_OPS.get(type(node.op))
            if op is None:
                raise SafeParseError(f"Binary operator '{type(node.op).__name__}' is not permitted.")
            left = self._convert(node.left, safe_locals)
            right = self._convert(node.right, safe_locals)
            return op(left, right)

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise SafeParseError("Only direct allowlisted function calls are permitted.")
            if node.keywords:
                raise SafeParseError("Keyword arguments are not permitted.")
            if any(isinstance(arg, ast.Starred) for arg in node.args):
                raise SafeParseError("Starred arguments are not permitted.")

            name = node.func.id
            if name == "Symbol":
                if len(node.args) != 1 or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                    raise SafeParseError("Symbol() requires exactly one literal string name.")
                return self.make_symbol(node.args[0].value)

            if name not in safe_locals:
                raise SafeParseError(f"Function '{name}' is not allowlisted.")

            target = safe_locals[name]
            if name in {"pi", "E", "I", "oo", "nan", "zoo"}:
                raise SafeParseError(f"'{name}' is a constant, not a callable.")

            args = [self._convert(arg, safe_locals) for arg in node.args]

            if name == "Rational" and len(args) not in {1, 2}:
                raise SafeParseError("Rational() accepts one or two arguments.")
            if name in {"Integer", "Float"} and len(args) not in {1, 2}:
                raise SafeParseError(f"{name}() accepts one or two arguments.")

            if not callable(target):
                raise SafeParseError(f"'{name}' is not callable.")
            if not _is_safe_binding(target):
                raise SafeParseError(f"Call target '{name}' is not a permitted SymPy callable.")
            try:
                return target(*args)
            except Exception as exc:
                raise SafeParseError(
                    f"Safe mathematical call '{name}' failed: {type(exc).__name__}: {exc}"
                ) from exc

        raise SafeParseError(
            f"Syntax node '{type(node).__name__}' is not permitted in mathematical expressions."
        )

    def parse(
        self,
        expr_str: str,
        extra_locals: Optional[Dict[str, Any]] = None,
    ) -> sp.Expr:
        if not isinstance(expr_str, str):
            raise SafeParseError(
                f"Expression must be a string, got {type(expr_str).__name__}."
            )

        s = expr_str.strip()
        if not s:
            raise SafeParseError("Empty expression string.")

        self._check_string(s)

        safe_locals = dict(self._base_locals)
        if extra_locals:
            self._validate_bindings(extra_locals, "extra_locals")
            safe_locals.update(extra_locals)

        t0 = time.monotonic()
        try:
            tree = ast.parse(s, mode="eval")
        except (SyntaxError, ValueError, TypeError) as exc:
            raise SafeParseError(f"Mathematical syntax is invalid: {exc}") from exc

        node_count, ast_depth = _ast_stats(tree)
        if node_count > _MAX_AST_NODES:
            raise SafeParseError(
                f"Expression AST has {node_count} nodes (max {_MAX_AST_NODES}). Possible DoS payload."
            )
        if ast_depth > self.max_depth:
            raise SafeParseError(
                f"Expression AST depth is {ast_depth} (max {self.max_depth}). Possible DoS payload."
            )

        try:
            expr = self._convert(tree.body, safe_locals)
        except SafeParseError:
            raise
        except Exception as exc:
            raise SafeParseError(
                f"Unexpected safe-conversion error: {type(exc).__name__}: {exc}"
            ) from exc

        elapsed = time.monotonic() - t0
        if elapsed > self.max_seconds:
            raise SafeParseError(
                f"Parse exceeded time limit of {self.max_seconds}s "
                f"(took {elapsed:.2f}s)."
            )

        if not isinstance(expr, sp.Basic):
            raise SafeParseError(
                f"Parser produced unsupported object type {type(expr).__name__}."
            )

        self._check_expr(expr)
        return expr

    def parse_equation(
        self,
        eq_str: str,
        extra_locals: Optional[Dict[str, Any]] = None,
    ) -> sp.Expr:
        if not isinstance(eq_str, str):
            raise SafeParseError(
                f"Equation must be a string, got {type(eq_str).__name__}."
            )
        s = eq_str.strip()
        self._check_string(s)

        if "=" in s:
            if "==" in s:
                raise SafeParseError(
                    "Double == in equation string. Use single = for math equality."
                )
            lhs_str, rhs_str = s.split("=", 1)
            if not lhs_str.strip() or not rhs_str.strip():
                raise SafeParseError("Equation must contain both left and right expressions.")
            lhs = self.parse(lhs_str.strip(), extra_locals)
            rhs = self.parse(rhs_str.strip(), extra_locals)
            return sp.nsimplify(lhs - rhs, rational=False)

        return self.parse(s, extra_locals)

    def make_symbol(self, name: str, **assumptions: Any) -> sp.Symbol:
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
            raise SafeParseError(
                f"Symbol name '{name}' is not a valid identifier. "
                "Must start with a letter and contain only alphanumeric characters and underscores."
            )
        return sp.Symbol(name, **assumptions)

    def make_function(self, name: str) -> type:
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
            raise SafeParseError(
                f"Function name '{name}' is not a valid identifier."
            )
        return sp.Function(name)
