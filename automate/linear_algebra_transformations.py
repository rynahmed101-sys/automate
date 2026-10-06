"""Orthogonal and unitary matrix property verification.

This isolated Stage 1A helper provides reusable transformation semantics without
registering a new agent rule. The primary integration pass can expose the
verified functions through the central rule registry once reconciled with
current-main contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import sympy as sp

from automate.ir.linear_algebra import (
    LinearAlgebraParseError,
    ParsedLinearAlgebra,
    parse_linear_algebra_expression,
)

MatrixProperty = Literal["orthogonal", "unitary"]


@dataclass(frozen=True)
class MatrixPropertyVerification:
    property: MatrixProperty
    passed: bool
    status: str
    matrix_shape: tuple[int, int] | None
    residual_left: tuple[tuple[str, ...], ...] | None
    residual_right: tuple[tuple[str, ...], ...] | None
    numpy_cross_check: dict[str, Any]
    error: str | None = None


def _zero_state(expr: sp.Expr) -> bool | None:
    """Return True/False only when symbolic zero-ness is established."""
    try:
        reduced = sp.simplify(expr)
    except Exception:
        return None
    if reduced == 0 or reduced.is_zero is True:
        return True
    if reduced.is_zero is False:
        return False
    try:
        proved = reduced.equals(0)
    except Exception:
        proved = None
    return proved if proved in (True, False) else None


def _matrix_zero_state(matrix: sp.MatrixBase) -> bool | None:
    states = [_zero_state(value) for value in matrix]
    if any(state is False for state in states):
        return False
    if all(state is True for state in states):
        return True
    return None


def _matrix_strings(matrix: sp.MatrixBase) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(str(sp.simplify(matrix[i, j])) for j in range(matrix.cols))
        for i in range(matrix.rows)
    )


def _numeric_matrix(parsed: ParsedLinearAlgebra) -> np.ndarray | None:
    matrix = sp.Matrix(parsed.value)
    values: list[list[complex | float]] = []
    for i in range(matrix.rows):
        row: list[complex | float] = []
        for j in range(matrix.cols):
            value = matrix[i, j]
            if not value.is_number:
                return None
            try:
                numeric = complex(sp.N(value, 16))
            except Exception:
                return None
            row.append(float(numeric.real) if abs(numeric.imag) < 1e-14 else numeric)
        values.append(row)
    return np.asarray(values)


def verify_matrix_property(
    matrix_text: str,
    property: MatrixProperty,
    *,
    rtol: float = 1e-9,
    atol: float = 1e-10,
) -> MatrixPropertyVerification:
    """Verify a square matrix is orthogonal or unitary.

    Orthogonal means a real matrix Q satisfying Q.T*Q = Q*Q.T = I.
    Unitary means a complex-capable matrix U satisfying U.H*U = U*U.H = I.

    Symbolic ambiguity returns UNVERIFIED. Definite violations return FAILED.
    Numeric inputs receive an independent NumPy product check as supporting
    evidence; that check never upgrades an unresolved symbolic claim.
    """
    if property not in {"orthogonal", "unitary"}:
        raise ValueError("property must be 'orthogonal' or 'unitary'.")

    try:
        parsed = parse_linear_algebra_expression(matrix_text)
    except LinearAlgebraParseError as exc:
        return MatrixPropertyVerification(
            property, False, "FAILED", None, None, None,
            {"available": False, "independence_class": "NOT_AVAILABLE"},
            f"Invalid matrix expression: {exc}",
        )

    if parsed.kind != "matrix":
        return MatrixPropertyVerification(
            property, False, "FAILED", None, None, None,
            {"available": False, "independence_class": "NOT_AVAILABLE"},
            "Matrix-property verification requires a matrix expression.",
        )

    matrix = sp.Matrix(parsed.value)
    shape = (int(matrix.rows), int(matrix.cols))
    if matrix.rows != matrix.cols:
        return MatrixPropertyVerification(
            property, False, "FAILED", shape, None, None,
            {"available": False, "independence_class": "NOT_AVAILABLE"},
            f"{property} matrices must be square; received shape {shape}.",
        )

    if property == "orthogonal":
        reality_states = [_zero_state(sp.im(value)) for value in matrix]
        if any(state is False for state in reality_states):
            return MatrixPropertyVerification(
                property, False, "FAILED", shape, None, None,
                {"available": False, "independence_class": "NOT_APPLICABLE"},
                "Orthogonal matrices must have real entries.",
            )
        if not all(state is True for state in reality_states):
            return MatrixPropertyVerification(
                property, False, "UNVERIFIED", shape, None, None,
                {"available": False, "independence_class": "NOT_AVAILABLE"},
                "Reality of all matrix entries cannot be established symbolically.",
            )
        adjoint = matrix.T
    else:
        adjoint = matrix.conjugate().T

    identity = sp.eye(matrix.rows)
    left = sp.simplify(adjoint * matrix - identity)
    right = sp.simplify(matrix * adjoint - identity)
    left_state = _matrix_zero_state(left)
    right_state = _matrix_zero_state(right)

    numeric = _numeric_matrix(parsed)
    if numeric is None:
        cross: dict[str, Any] = {
            "available": False,
            "independence_class": "NOT_AVAILABLE",
        }
    else:
        try:
            adjoint_np = numeric.T.conj() if property == "unitary" else numeric.T
            left_np = adjoint_np @ numeric
            right_np = numeric @ adjoint_np
            expected = np.eye(matrix.rows)
            cross = {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.matrix_products",
                "passed": bool(
                    np.allclose(left_np, expected, rtol=rtol, atol=atol, equal_nan=False)
                    and np.allclose(right_np, expected, rtol=rtol, atol=atol, equal_nan=False)
                ),
                "rtol": rtol,
                "atol": atol,
            }
        except (TypeError, ValueError, np.linalg.LinAlgError) as exc:
            cross = {
                "available": False,
                "independence_class": "NOT_AVAILABLE",
                "reason": f"NumPy cross-check failed: {type(exc).__name__}: {exc}",
            }

    residual_left = _matrix_strings(left)
    residual_right = _matrix_strings(right)

    if left_state is True and right_state is True:
        return MatrixPropertyVerification(
            property, True, "SYMBOLIC_CHECKED", shape,
            residual_left, residual_right, cross,
        )
    if left_state is False or right_state is False:
        return MatrixPropertyVerification(
            property, False, "FAILED", shape,
            residual_left, residual_right, cross,
            "At least one defining matrix-product identity is non-zero.",
        )
    return MatrixPropertyVerification(
        property, False, "UNVERIFIED", shape,
        residual_left, residual_right, cross,
        "A defining matrix-product identity could not be established as zero.",
    )


def verify_orthogonal_matrix(
    matrix_text: str, *, rtol: float = 1e-9, atol: float = 1e-10
) -> MatrixPropertyVerification:
    return verify_matrix_property(
        matrix_text, "orthogonal", rtol=rtol, atol=atol
    )


def verify_unitary_matrix(
    matrix_text: str, *, rtol: float = 1e-9, atol: float = 1e-10
) -> MatrixPropertyVerification:
    return verify_matrix_property(
        matrix_text, "unitary", rtol=rtol, atol=atol
    )
