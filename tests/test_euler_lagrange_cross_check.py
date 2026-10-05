"""
Cross-check tests for Euler-Lagrange equations.

These tests verify that Automate's manual EL derivation in LagrangianSystem
matches SymPy's independent sympy.calculus.euler.euler_equations.

Independence classification: SAME_ENGINE_DIFFERENT_PATH
    - Both use SymPy, but via completely different code paths
    - Our code: manual partial derivatives + time derivative
    - SymPy's: sympy.calculus.euler module (variational calculus)

Reference values verified against textbook results where applicable.
"""

import pytest
import sympy as sp

from automate.mechanics.lagrangian import LagrangianSystem

pytestmark = pytest.mark.same_engine_different_path


# ---------------------------------------------------------------------------
# A. Simple Harmonic Oscillator (1D)
# ---------------------------------------------------------------------------

class TestCrossCheckSHO:

    def test_sho_cross_check_matches(self):
        """SHO: L = m*x_dot²/2 - k*x²/2 → EoM: m*x_ddot + k*x = 0."""
        sys = LagrangianSystem(
            lagrangian="m * x_dot**2 / 2 - k * x**2 / 2",
            coordinates=["x"],
            parameters={"m": "positive", "k": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"SHO cross-check failed: {report['discrepancies']}"
        assert report["independence_class"] == "SAME_ENGINE_DIFFERENT_PATH"

    @pytest.mark.textbook_reference
    def test_sho_eom_is_correct(self):
        """Verify the EoM itself: m*x_ddot + k*x = 0."""
        sys = LagrangianSystem(
            lagrangian="m * x_dot**2 / 2 - k * x**2 / 2",
            coordinates=["x"],
            parameters={"m": "positive", "k": "positive"},
        )
        passed, details, _, err = sys.verify_euler_lagrange("m * x_ddot + k * x")
        assert passed, f"SHO EoM verification failed: {err}"
        # Cross-check should be embedded in details
        assert "sympy_euler_cross_check" in details
        assert details["sympy_euler_cross_check"]["all_matched"] is True


# ---------------------------------------------------------------------------
# B. Gravity (constant force, 1D)
# ---------------------------------------------------------------------------

class TestCrossCheckGravity:

    def test_gravity_cross_check_matches(self):
        """Gravity: L = m*x_dot²/2 - m*g*x → EoM: m*x_ddot + m*g = 0."""
        sys = LagrangianSystem(
            lagrangian="m * x_dot**2 / 2 - m * g * x",
            coordinates=["x"],
            parameters={"m": "positive", "g": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"Gravity cross-check failed: {report['discrepancies']}"

    @pytest.mark.textbook_reference
    def test_gravity_eom_is_correct(self):
        """Verify: m*x_ddot + m*g = 0 (i.e. x_ddot = -g)."""
        sys = LagrangianSystem(
            lagrangian="m * x_dot**2 / 2 - m * g * x",
            coordinates=["x"],
            parameters={"m": "positive", "g": "positive"},
        )
        passed, details, _, err = sys.verify_euler_lagrange("m * x_ddot + m * g")
        assert passed, f"Gravity EoM verification failed: {err}"


# ---------------------------------------------------------------------------
# C. Polar Kinetic Energy with Potential (2 coordinates)
# ---------------------------------------------------------------------------

class TestCrossCheckPolar:

    def test_polar_cross_check_matches(self):
        """Polar: L = m*(r_dot² + r²*theta_dot²)/2 - V(r).
        Since V(r) is abstract, we use a concrete V = k*r²/2."""
        sys = LagrangianSystem(
            lagrangian="m * (r_dot**2 + r**2 * theta_dot**2) / 2 - k * r**2 / 2",
            coordinates=["r", "theta"],
            parameters={"m": "positive", "k": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"Polar cross-check failed: {report['discrepancies']}"

    def test_polar_theta_eom_angular_momentum(self):
        """For central force, theta EoM should be d/dt(m*r²*theta_dot) = 0."""
        sys = LagrangianSystem(
            lagrangian="m * (r_dot**2 + r**2 * theta_dot**2) / 2 - k * r**2 / 2",
            coordinates=["r", "theta"],
            parameters={"m": "positive", "k": "positive"},
        )
        eoms, _ = sys.euler_lagrange_equations()
        # theta EoM should involve d/dt(m*r²*theta_dot) = 0
        # In algebraic form: m*(2*r*r_dot*theta_dot + r²*theta_ddot) = 0
        theta_eom = sys.to_algebraic(eoms["theta"])
        r, r_dot = sp.Symbol("r", real=True), sp.Symbol("r_dot", real=True)
        theta_ddot = sp.Symbol("theta_ddot", real=True)
        m = sp.Symbol("m", positive=True)
        # Should contain m*r²*theta_ddot term
        assert theta_ddot in theta_eom.free_symbols


# ---------------------------------------------------------------------------
# D. Coupled Oscillators (2 coordinates, coupling term)
# ---------------------------------------------------------------------------

class TestCrossCheckCoupledOscillators:

    def test_coupled_oscillators_cross_check(self):
        """Two masses on springs: L = m*(x1_dot² + x2_dot²)/2 - k*(x1² + x2²)/2 - c*(x1-x2)²/2."""
        sys = LagrangianSystem(
            lagrangian="m * (x1_dot**2 + x2_dot**2) / 2 - k * (x1**2 + x2**2) / 2 - c * (x1 - x2)**2 / 2",
            coordinates=["x1", "x2"],
            parameters={"m": "positive", "k": "positive", "c": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"Coupled oscillators cross-check failed: {report['discrepancies']}"


# ---------------------------------------------------------------------------
# E. Pendulum (nonlinear, 1D)
# ---------------------------------------------------------------------------

class TestCrossCheckPendulum:

    def test_pendulum_cross_check(self):
        """Simple pendulum: L = m*l²*theta_dot²/2 + m*g*l*cos(theta)."""
        sys = LagrangianSystem(
            lagrangian="m * l**2 * theta_dot**2 / 2 + m * g * l * cos(theta)",
            coordinates=["theta"],
            parameters={"m": "positive", "g": "positive", "l": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"Pendulum cross-check failed: {report['discrepancies']}"

    @pytest.mark.textbook_reference
    def test_pendulum_eom_correct(self):
        """Pendulum EoM: m*l²*theta_ddot + m*g*l*sin(theta) = 0."""
        sys = LagrangianSystem(
            lagrangian="m * l**2 * theta_dot**2 / 2 + m * g * l * cos(theta)",
            coordinates=["theta"],
            parameters={"m": "positive", "g": "positive", "l": "positive"},
        )
        passed, _, _, err = sys.verify_euler_lagrange(
            "m * l**2 * theta_ddot + m * g * l * sin(theta)"
        )
        assert passed, f"Pendulum EoM verification failed: {err}"


# ---------------------------------------------------------------------------
# F. Relativistic free particle (1D, velocity-dependent)
# ---------------------------------------------------------------------------

class TestCrossCheckRelativistic:

    def test_relativistic_cross_check(self):
        """Relativistic 1D free particle: L = -m*c²*sqrt(1 - x_dot²/c²).
        Use concrete c=1 for simplicity."""
        sys = LagrangianSystem(
            lagrangian="-m * sqrt(1 - x_dot**2)",
            coordinates=["x"],
            parameters={"m": "positive"},
        )
        report = sys.cross_check_euler_lagrange()
        assert report["all_matched"] is True, \
            f"Relativistic cross-check failed: {report['discrepancies']}"
