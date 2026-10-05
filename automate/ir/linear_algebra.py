"""Safe typed parsing primitives for Phase 1A linear algebra."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

import sympy as sp

from automate.ir.safe_parser import SafeParseError, SafeParser

_MAX_LA_STRING = 4096
_MAX_LA_DIM = 64


class LinearAlgebraParseError(ValueError):
    """Raised when a vector/matrix expression is not safely representable."""


@dataclass(frozen=True)
class ParsedLinearAlgebra:
    kind: str
    value: sp.Expr | sp.MatrixBase

    @property
    def shape(self) -> tuple[int, ...]:
        if self.kind == "scalar":
            return ()
        if self.kind == "vector":
            return (int(self.value.rows),)
        return (int(self.value.rows), int(self.value.cols))


def _literal_sequence(node: ast.AST, label: str) -> list[ast.AST]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise LinearAlgebraParseError(f"{label} must be a literal list or tuple.")
    return list(node.elts)


def _parse_scalar_node(node: ast.AST, parser: SafeParser) -> sp.Expr:
    try:
        value = parser.parse(ast.unparse(node))
    except (AttributeError, SafeParseError) as exc:
        raise LinearAlgebraParseError(f"Unsafe scalar entry: {exc}") from exc
    if not isinstance(value, sp.Expr):
        raise LinearAlgebraParseError(
            f"Scalar entry produced unsupported type {type(value).__name__}."
        )
    return value


def _parse_vector(call: ast.Call, parser: SafeParser) -> ParsedLinearAlgebra:
    if call.keywords or len(call.args) != 1 or any(isinstance(a, ast.Starred) for a in call.args):
        raise LinearAlgebraParseError(
            "Vector() requires exactly one positional literal argument."
        )
    cells = _literal_sequence(call.args[0], "Vector data")
    if not cells:
        raise LinearAlgebraParseError("Vector data must not be empty.")
    if len(cells) > _MAX_LA_DIM:
        raise LinearAlgebraParseError(f"Vector length exceeds {_MAX_LA_DIM}.")
    return ParsedLinearAlgebra("vector", sp.Matrix([
        _parse_scalar_node(cell, parser) for cell in cells
    ]))


def _parse_matrix(call: ast.Call, parser: SafeParser) -> ParsedLinearAlgebra:
    if call.keywords or len(call.args) != 1 or any(isinstance(a, ast.Starred) for a in call.args):
        raise LinearAlgebraParseError(
            "Matrix() requires exactly one positional literal argument."
        )
    row_nodes = _literal_sequence(call.args[0], "Matrix data")
    if not row_nodes:
        raise LinearAlgebraParseError("Matrix data must contain at least one row.")
    if len(row_nodes) > _MAX_LA_DIM:
        raise LinearAlgebraParseError(f"Matrix row count exceeds {_MAX_LA_DIM}.")
    rows: list[list[sp.Expr]] = []
    expected_cols: int | None = None
    for row_index, row_node in enumerate(row_nodes):
        cells = _literal_sequence(row_node, f"Matrix row {row_index}")
        if not cells and any(_literal_sequence(row, f"Matrix row {idx}") for idx, row in enumerate(row_nodes)):
            raise LinearAlgebraParseError("Matrix rows must not mix empty and non-empty rows.")
        if len(cells) > _MAX_LA_DIM:
            raise LinearAlgebraParseError(f"Matrix column count exceeds {_MAX_LA_DIM}.")
        if expected_cols is None:
            expected_cols = len(cells)
        elif len(cells) != expected_cols:
            raise LinearAlgebraParseError(
                f"Matrix rows have inconsistent lengths: expected {expected_cols}, got {len(cells)}."
            )
        rows.append([_parse_scalar_node(cell, parser) for cell in cells])
    if all(len(row) == 0 for row in rows):
        # A rectangular zero-column matrix is needed to represent zero-dimensional
        # subspaces without inventing a fake basis vector.
        return ParsedLinearAlgebra("matrix", sp.zeros(len(rows), 0))
    return ParsedLinearAlgebra("matrix", sp.Matrix(rows))


def parse_linear_algebra_expression(text: str) -> ParsedLinearAlgebra:
    """Parse a scalar, Vector([...]), or Matrix([[...], ...]) safely."""
    if not isinstance(text, str):
        raise LinearAlgebraParseError(
            f"Expression must be a string, got {type(text).__name__}."
        )
    source = text.strip()
    if not source:
        raise LinearAlgebraParseError("Empty linear-algebra expression.")
    if len(source) > _MAX_LA_STRING:
        raise LinearAlgebraParseError(f"Expression exceeds {_MAX_LA_STRING} characters.")
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, ValueError, TypeError) as exc:
        raise LinearAlgebraParseError(f"Invalid linear-algebra syntax: {exc}") from exc

    parser = SafeParser()
    if isinstance(tree.body, ast.Call):
        if not isinstance(tree.body.func, ast.Name):
            raise LinearAlgebraParseError(
                "Only direct Vector() or Matrix() constructors are supported."
            )
        name = tree.body.func.id
        if name in {"Vector", "vector"}:
            return _parse_vector(tree.body, parser)
        if name in {"Matrix", "matrix"}:
            return _parse_matrix(tree.body, parser)
        raise LinearAlgebraParseError(
            "Only Vector() or Matrix() constructors are supported for non-scalar values."
        )

    try:
        value = parser.parse(source)
    except SafeParseError as exc:
        raise LinearAlgebraParseError(str(exc)) from exc
    if not isinstance(value, sp.Expr):
        raise LinearAlgebraParseError(
            f"Scalar expression produced unsupported type {type(value).__name__}."
        )
    return ParsedLinearAlgebra("scalar", value)


def linear_algebra_ast(parsed: ParsedLinearAlgebra) -> dict[str, Any]:
    if parsed.kind == "scalar":
        return {"kind": "scalar", "shape": [], "value": str(parsed.value)}
    if parsed.kind == "vector":
        matrix = sp.Matrix(parsed.value)
        return {
            "kind": "vector",
            "shape": [int(matrix.rows)],
            "entries": [str(matrix[i, 0]) for i in range(matrix.rows)],
        }
    matrix = sp.Matrix(parsed.value)
    return {
        "kind": "matrix",
        "shape": [int(matrix.rows), int(matrix.cols)],
        "entries": [[str(matrix[i, j]) for j in range(matrix.cols)] for i in range(matrix.rows)],
    }
