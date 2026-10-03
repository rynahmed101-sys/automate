"""
Tests for the 4 newly implemented algebraic rule verifiers:
  - divide_both_sides
  - differentiate_both_sides
  - substitute
  - simplify

Each test calls the verifier directly via SymPyChecker dispatch and verifies:
  1. Correct step accepted.
  2. Wrong result (wrong coefficient, wrong form) rejected.
  3. Missing required parameter rejected.
  4. Injected expression rejected by SafeParser.

Tests are INDEPENDENT — expected values are pre-computed by hand or trivially
verified against known calculus results (power rule, linearity, substitution).
"""

import pytest
import sympy as sp
from unittest.mock import MagicMock

from automate.backend.sympy_backend import SymPyChecker
from automate.core.status import VerificationStatus


def _make_node(expr_str: str) -> MagicMock:
    """Minimal stand-in for a DerivationNode."""
    node = MagicMock()
    node.expression = MagicMock()
    node.expression.raw_str = expr_str
    return node


def _make_edge(rule: str, params: dict) -> MagicMock:
    edge = MagicMock()
    edge.transformation_rule = rule
    edge.parameters = params
    return edge


def _run(rule: str, in_expr: str, out_expr: str, params: dict):
    """Helper: directly call the relevant private verifier method."""
    checker = SymPyChecker()
    in_node  = _make_node(in_expr)
    out_node = _make_node(out_expr)
    if rule == "divide_both_sides":
        return checker._verify_divide_both_sides(in_node, out_node, params)
    elif rule == "differentiate_both_sides":
        return checker._verify_differentiate_both_sides(in_node, out_node, params)
    elif rule == "substitute":
        return checker._verify_substitute(in_node, out_node, params)
    elif rule == "simplify":
        return checker._verify_simplify(in_node, out_node)
    else:
        raise ValueError(f"Unknown rule: {rule}")


# ---------------------------------------------------------------------------
# A. divide_both_sides
# ---------------------------------------------------------------------------

class TestDivideBothSides:

    def test_divide_linear_by_m_correct(self):
        """m*a = F  divided by m  →  a = F/m"""
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="m * a",
            out_expr="a",
            params={"divisor": "m"},
        )
        assert passed, f"Should pass: {err}"

    def test_divide_quadratic_correct(self):
        """2*x**2 divided by 2 → x**2"""
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="2 * x**2",
            out_expr="x**2",
            params={"divisor": "2"},
        )
        assert passed, f"Should pass: {err}"

    def test_divide_wrong_result_rejected(self):
        """m*a divided by m claimed to give 2*a — must fail."""
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="m * a",
            out_expr="2 * a",
            params={"divisor": "m"},
        )
        assert not passed, "Wrong result should fail"

    def test_divide_by_zero_rejected(self):
        """Divisor = 0 must be rejected."""
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="m * a",
            out_expr="a",
            params={"divisor": "0"},
        )
        assert not passed
        assert "zero" in (err or "").lower()

    def test_missing_divisor_rejected(self):
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="m * a",
            out_expr="a",
            params={},
        )
        assert not passed
        assert "divisor" in (err or "").lower()

    def test_injected_divisor_rejected(self):
        passed, details, steps, err = _run(
            "divide_both_sides",
            in_expr="m * a",
            out_expr="a",
            params={"divisor": "__import__('os')"},
        )
        assert not passed


# ---------------------------------------------------------------------------
# B. differentiate_both_sides
# ---------------------------------------------------------------------------

class TestDifferentiateBothSides:

    def test_diff_polynomial_correct(self):
        """d(x**2)/dx = 2*x"""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="x**2",
            out_expr="2*x",
            params={"wrt": "x"},
        )
        assert passed, f"Should pass: {err}"

    def test_diff_sin_correct(self):
        """d(sin(x))/dx = cos(x)"""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="sin(x)",
            out_expr="cos(x)",
            params={"wrt": "x"},
        )
        assert passed, f"Should pass: {err}"

    def test_diff_exp_correct(self):
        """d(exp(x))/dx = exp(x)"""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="exp(x)",
            out_expr="exp(x)",
            params={"wrt": "x"},
        )
        assert passed, f"Should pass: {err}"

    def test_diff_constant_correct(self):
        """d(5)/dx = 0"""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="5",
            out_expr="0",
            params={"wrt": "x"},
        )
        assert passed, f"Should pass: {err}"

    def test_diff_wrong_result_rejected(self):
        """d(x**2)/dx claimed to be 3*x — must fail (correct is 2*x)."""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="x**2",
            out_expr="3*x",
            params={"wrt": "x"},
        )
        assert not passed, "Wrong derivative must be rejected"

    def test_diff_missing_wrt_rejected(self):
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="x**2",
            out_expr="2*x",
            params={},
        )
        assert not passed
        assert "wrt" in (err or "").lower()

    def test_diff_injected_wrt_rejected(self):
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="x**2",
            out_expr="2*x",
            params={"wrt": "__import__('os')"},
        )
        assert not passed

    def test_diff_wrong_variable_rejected(self):
        """d(x**2)/dt = 0 (x doesn't depend on t); claiming 2*x is wrong."""
        passed, details, steps, err = _run(
            "differentiate_both_sides",
            in_expr="x**2",
            out_expr="2*x",
            params={"wrt": "t"},
        )
        assert not passed


# ---------------------------------------------------------------------------
# C. substitute
# ---------------------------------------------------------------------------

class TestSubstitute:

    def test_substitute_omega_into_ode(self):
        """
        In SHO: m*x_ddot + k*x = 0
        Substitute k → m*omega**2
        Result: m*x_ddot + m*omega**2*x = 0
        """
        passed, details, steps, err = _run(
            "substitute",
            in_expr="m * x_ddot + k * x",
            out_expr="m * x_ddot + m * omega**2 * x",
            params={"from": "k", "to": "m * omega**2"},
        )
        assert passed, f"Should pass: {err}"

    def test_substitute_simple_correct(self):
        """(x + 1).subs(x, 3) = 4"""
        passed, details, steps, err = _run(
            "substitute",
            in_expr="x + 1",
            out_expr="4",
            params={"from": "x", "to": "3"},
        )
        assert passed, f"Should pass: {err}"

    def test_substitute_wrong_result_rejected(self):
        """(x + 1).subs(x, 3) claimed to give 5 — wrong."""
        passed, details, steps, err = _run(
            "substitute",
            in_expr="x + 1",
            out_expr="5",
            params={"from": "x", "to": "3"},
        )
        assert not passed, "Wrong substitution result must be rejected"

    def test_substitute_missing_from_rejected(self):
        passed, details, steps, err = _run(
            "substitute",
            in_expr="x + 1",
            out_expr="4",
            params={"to": "3"},
        )
        assert not passed
        assert "from" in (err or "").lower()

    def test_substitute_injected_expression_rejected(self):
        passed, details, steps, err = _run(
            "substitute",
            in_expr="x + 1",
            out_expr="4",
            params={"from": "x", "to": "__import__('os').system('id')"},
        )
        assert not passed

    def test_substitute_symbolic_equivalence(self):
        """
        sin(x)**2 + cos(x)**2 substituted to 1.
        subs(sin(x)**2, 1 - cos(x)**2) gives 1 - cos(x)**2 + cos(x)**2 = 1.
        """
        passed, details, steps, err = _run(
            "substitute",
            in_expr="sin(x)**2 + cos(x)**2",
            out_expr="1",
            params={"from": "sin(x)**2", "to": "1 - cos(x)**2"},
        )
        assert passed, f"Trig identity via substitution should pass: {err}"


# ---------------------------------------------------------------------------
# D. simplify
# ---------------------------------------------------------------------------

class TestSimplify:

    def test_simplify_trig_identity(self):
        """sin(x)**2 + cos(x)**2 → 1  (Pythagorean identity)."""
        passed, details, steps, err = _run(
            "simplify",
            in_expr="sin(x)**2 + cos(x)**2",
            out_expr="1",
            params={},
        )
        assert passed, f"Should pass: {err}"

    def test_simplify_polynomial(self):
        """(x + 1)**2 - x**2 - 2*x → 1."""
        passed, details, steps, err = _run(
            "simplify",
            in_expr="(x + 1)**2 - x**2 - 2*x",
            out_expr="1",
            params={},
        )
        assert passed, f"Should pass: {err}"

    def test_simplify_exp_log(self):
        """exp(log(x)) → x  (for x > 0)."""
        passed, details, steps, err = _run(
            "simplify",
            in_expr="exp(log(x))",
            out_expr="x",
            params={},
        )
        assert passed, f"Should pass: {err}"

    def test_simplify_wrong_result_rejected(self):
        """sin(x)**2 + cos(x)**2 claimed to equal 2 — must fail."""
        passed, details, steps, err = _run(
            "simplify",
            in_expr="sin(x)**2 + cos(x)**2",
            out_expr="2",
            params={},
        )
        assert not passed, "Wrong simplification must be rejected"

    def test_simplify_zero_is_zero(self):
        """0 simplifies to 0."""
        passed, details, steps, err = _run(
            "simplify",
            in_expr="0",
            out_expr="0",
            params={},
        )
        assert passed, f"Should pass: {err}"

    def test_simplify_injected_expression_rejected(self):
        passed, details, steps, err = _run(
            "simplify",
            in_expr="__import__('os').system('id')",
            out_expr="0",
            params={},
        )
        assert not passed
