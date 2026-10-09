import sympy as sp

from automate import calculate


def test_solve_accepts_native_sympy_expression():
    x = sp.Symbol("x")
    assert calculate("solve", x**2 - 4, variable="x") == [-2, 2]


def test_solve_accepts_native_sympy_equation():
    x = sp.Symbol("x")
    assert calculate("solve", sp.Eq(x**2, 4), variable="x") == [-2, 2]
