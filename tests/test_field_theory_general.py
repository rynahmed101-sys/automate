"""
Tests for Generalized Variational Field Theory Engine:
Klein-Gordon field, phi^4 theory, coupled fields, and adversarial sign verification.
"""

import pytest
import sympy as sp
from automate.field_theory.variational import FieldTheoryAction


def test_klein_gordon_1d_spacetime():
    # 1+1D spacetime coordinates [t, x]
    # L = 1/2 * (d_t_phi)^2 - 1/2 * (d_x_phi)^2 - 1/2 * m^2 * phi^2
    action = FieldTheoryAction(
        lagrangian_density="1/2 * d_t_phi**2 - 1/2 * d_x_phi**2 - 1/2 * m**2 * phi**2",
        fields=["phi"],
        coordinates=["t", "x"],
        parameters={"m": "positive"},
        assumptions=["vanishing_boundary_variations"]
    )
    eoms, steps = action.euler_lagrange_field_equations()
    assert "phi" in eoms

    # Verify candidate equation: diff(phi(t,x), t, 2) - diff(phi(t,x), x, 2) + m^2 * phi(t,x) = 0
    t = action.coord_map["t"]
    x = action.coord_map["x"]
    phi = action.field_funcs["phi"]
    m = action.symbols["m"]

    expected_eq = sp.diff(phi, t, 2) - sp.diff(phi, x, 2) + m**2 * phi
    assert sp.simplify(eoms["phi"] - expected_eq) == 0

    # Verification method
    passed, details, _, err = action.verify_field_equation(
        "diff(phi, t, 2) - diff(phi, x, 2) + m**2 * phi = 0"
    )
    assert passed is True
    assert err is None


def test_phi4_nonlinear_scalar_field():
    # 1+1D phi^4 scalar field: L = 1/2*(d_t_phi)^2 - 1/2*(d_x_phi)^2 - 1/2*m^2*phi^2 - 1/4*lam*phi^4
    action = FieldTheoryAction(
        lagrangian_density="1/2 * d_t_phi**2 - 1/2 * d_x_phi**2 - 1/2 * m**2 * phi**2 - 1/4 * lam * phi**4",
        fields=["phi"],
        coordinates=["t", "x"],
        parameters={"m": "positive", "lam": "positive"},
        assumptions=["vanishing_boundary_variations"]
    )
    passed, details, _, _ = action.verify_field_equation(
        "diff(phi, t, 2) - diff(phi, x, 2) + m**2 * phi + lam * phi**3 = 0"
    )
    assert passed is True


def test_coupled_scalar_fields():
    # Two scalar fields phi1, phi2 with interaction g * phi1 * phi2
    action = FieldTheoryAction(
        lagrangian_density=(
            "1/2 * d_t_phi1**2 - 1/2 * d_x_phi1**2 "
            "+ 1/2 * d_t_phi2**2 - 1/2 * d_x_phi2**2 "
            "- 1/2 * m1**2 * phi1**2 - 1/2 * m2**2 * phi2**2 - g * phi1 * phi2"
        ),
        fields=["phi1", "phi2"],
        coordinates=["t", "x"],
        parameters={"m1": "positive", "m2": "positive", "g": "real"},
        assumptions=["vanishing_boundary_variations"]
    )
    passed, details, _, _ = action.verify_field_equation({
        "phi1": "diff(phi1, t, 2) - diff(phi1, x, 2) + m1**2 * phi1 + g * phi2 = 0",
        "phi2": "diff(phi2, t, 2) - diff(phi2, x, 2) + m2**2 * phi2 + g * phi1 = 0"
    })
    assert passed is True


def test_adversarial_wrong_field_equation():
    # Candidate equation has wrong sign on mass term
    action = FieldTheoryAction(
        lagrangian_density="1/2 * d_t_phi**2 - 1/2 * d_x_phi**2 - 1/2 * m**2 * phi**2",
        fields=["phi"],
        coordinates=["t", "x"],
        parameters={"m": "positive"},
        assumptions=["vanishing_boundary_variations"]
    )
    # Wrong equation: minus mass term instead of plus
    passed, _, _, err = action.verify_field_equation(
        "diff(phi, t, 2) - diff(phi, x, 2) - m**2 * phi = 0"
    )
    assert passed is False
    assert "residual non-zero" in err


def test_variational_verification_requires_boundary_assumption():
    action = FieldTheoryAction(
        lagrangian_density="1/2 * d_t_phi**2 - 1/2 * d_x_phi**2",
        fields=["phi"],
        coordinates=["t", "x"],
    )
    passed, _, _, err = action.verify_field_equation(
        "diff(phi, t, 2) - diff(phi, x, 2) = 0"
    )
    assert passed is False
    assert err.startswith("UNVERIFIED:")


def test_variational_verification_rejects_unknown_candidate_field():
    action = FieldTheoryAction(
        lagrangian_density="1/2 * d_t_phi**2",
        fields=["phi"],
        coordinates=["t"],
        assumptions=["vanishing_boundary_variations"],
    )
    passed, _, _, err = action.verify_field_equation({
        "phi": "diff(phi, t, 2) = 0",
        "psi": "0 = 0",
    })
    assert passed is False
    assert err.startswith("INVALID:")


def test_higher_order_field_derivative_fails_closed():
    with pytest.raises(ValueError, match="higher-order field derivatives"):
        FieldTheoryAction(
            lagrangian_density="d_t2_phi**2",
            fields=["phi"],
            coordinates=["t"],
            assumptions=["vanishing_boundary_variations"],
        )
