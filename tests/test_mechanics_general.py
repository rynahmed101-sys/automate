"""
Tests for Generalized Classical Mechanics: Multi-coordinate Lagrangians,
Pendulum, Central Forces, Hamiltonian construction, and Noether Conservation.
"""

import pytest
import sympy as sp
from automate.mechanics.lagrangian import LagrangianSystem


def test_harmonic_oscillator_lagrangian():
    sys = LagrangianSystem(
        lagrangian="1/2 * m * x_dot**2 - 1/2 * k * x**2",
        coordinates=["x"],
        parameters={"m": "positive", "k": "positive"}
    )
    eoms, steps = sys.euler_lagrange_equations()
    assert "x" in eoms
    # m*x_ddot + k*x
    passed, details, _, err = sys.verify_euler_lagrange("m * x_ddot + k * x = 0")
    assert passed is True
    assert err is None

    # Energy conservation
    e_passed, e_details, _, _ = sys.verify_energy_conservation("1/2 * m * x_dot**2 + 1/2 * k * x**2")
    assert e_passed is True

    # Adversarial: wrong EoM sign
    bad_passed, _, _, bad_err = sys.verify_euler_lagrange("m * x_ddot - k * x = 0")
    assert bad_passed is False
    assert "residual mismatch" in bad_err


def test_simple_pendulum_angular_coordinate():
    # Angle theta (dimensionless coordinate)
    sys = LagrangianSystem(
        lagrangian="1/2 * m * l**2 * theta_dot**2 + m * g * l * cos(theta)",
        coordinates=["theta"],
        parameters={"m": "positive", "l": "positive", "g": "positive"}
    )
    eoms, _ = sys.euler_lagrange_equations()
    # d/dt(m*l^2*theta_dot) - (-m*g*l*sin(theta)) = m*l^2*theta_ddot + m*g*l*sin(theta) = 0
    passed, details, _, _ = sys.verify_euler_lagrange("m * l**2 * theta_ddot + m * g * l * sin(theta) = 0")
    assert passed is True

    # Energy conservation: E = 1/2*m*l^2*theta_dot^2 - m*g*l*cos(theta)
    e_passed, _, _, _ = sys.verify_energy_conservation("1/2 * m * l**2 * theta_dot**2 - m * g * l * cos(theta)")
    assert e_passed is True

    # Canonical momentum p_theta = m*l^2*theta_dot
    momenta = sys.canonical_momenta()
    assert sp.simplify(momenta["theta"] - sys.symbols["m"] * sys.symbols["l"]**2 * sys.q_dots["theta"]) == 0


def test_central_force_polar_coordinates_noether_angular_momentum():
    # 2D Central force in polar coordinates (r, theta): L = 1/2*m*(r_dot^2 + r^2*theta_dot^2) - V(r) with V = -k/r
    sys = LagrangianSystem(
        lagrangian="1/2 * m * (r_dot**2 + r**2 * theta_dot**2) + k / r",
        coordinates=["r", "theta"],
        parameters={"m": "positive", "k": "positive"}
    )
    eoms, _ = sys.euler_lagrange_equations()
    assert "r" in eoms
    assert "theta" in eoms

    # Verify r EoM: m*r_ddot - m*r*theta_dot^2 + k/r^2 = 0
    # Verify theta EoM: d/dt(m*r^2*theta_dot) = 2*m*r*r_dot*theta_dot + m*r^2*theta_ddot = 0
    passed, _, _, _ = sys.verify_euler_lagrange({
        "r": "m * r_ddot - m * r * theta_dot**2 + k / r**2 = 0",
        "theta": "m * r**2 * theta_ddot + 2 * m * r * r_dot * theta_dot = 0"
    })
    assert passed is True

    # Noether symmetries: theta is cyclic (dL/dtheta = 0) -> p_theta is conserved!
    noether = sys.check_noether_conservation()
    conserved_coords = [q["coordinate"] for q in noether["conserved_quantities"] if q["type"] == "momentum"]
    assert "theta" in conserved_coords
    assert noether["time_independent"] is True


def test_free_particle_3d_momentum_conservation():
    sys = LagrangianSystem(
        lagrangian="1/2 * m * (x_dot**2 + y_dot**2 + z_dot**2)",
        coordinates=["x", "y", "z"],
        parameters={"m": "positive"}
    )
    eoms, _ = sys.euler_lagrange_equations()
    # m*x_ddot = 0, m*y_ddot = 0, m*z_ddot = 0
    passed, _, _, _ = sys.verify_euler_lagrange({
        "x": "m * x_ddot = 0",
        "y": "m * y_ddot = 0",
        "z": "m * z_ddot = 0"
    })
    assert passed is True

    # All coordinates are cyclic -> linear momentum (p_x, p_y, p_z) all conserved
    noether = sys.check_noether_conservation()
    conserved_coords = [q["coordinate"] for q in noether["conserved_quantities"] if q["type"] == "momentum"]
    assert set(conserved_coords) == {"x", "y", "z"}


def test_hamiltonian_legendre_transform():
    sys = LagrangianSystem(
        lagrangian="1/2 * m * x_dot**2 - 1/2 * k * x**2",
        coordinates=["x"],
        parameters={"m": "positive", "k": "positive"}
    )
    H, p_syms = sys.hamiltonian()
    # H = p_x^2 / (2*m) + 1/2*k*x^2
    p_x = p_syms["x"]
    expected_H = p_x**2 / (2 * sys.symbols["m"]) + sp.Rational(1, 2) * sys.symbols["k"] * sys.q_syms["x"]**2
    assert sp.simplify(H - expected_H) == 0
