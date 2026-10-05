"""Acceptance tests for Stage 2C advanced mechanics verification."""
import sympy as sp

from automate.mechanics import MechanicalSystemRepresentation, GeneralizedCoordinate, MechanicalConstraint
from automate.mechanics.advanced import ConstraintMechanicsVerifier, HamiltonEquationVerifier


def test_hamilton_equations_harmonic_oscillator():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")],
        kinetic_energy="m*x_dot**2/2",
        potential_energy="k*x**2/2",
        parameters={"m": "positive", "k": "positive"},
    )
    passed, details, err = HamiltonEquationVerifier(model.as_lagrangian_system()).verify()
    assert passed, (details, err)


def test_holonomic_multiplier_equation():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")],
        kinetic_energy="m*x_dot**2/2",
        constraints=[MechanicalConstraint(expression="x-L")],
        parameters={"m": "positive"},
    )
    equations = ConstraintMechanicsVerifier(model).equations()
    expr = str(equations["x"])\n    assert "m" in expr and "x_ddot" in expr and "lambda_1" in expr


def test_nonholonomic_constraint_is_not_silently_accepted():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")],
        kinetic_energy="m*x_dot**2/2",
        constraints=[MechanicalConstraint(expression="x_dot")],
    )
    model.constraints[0].kind = "nonholonomic"
    verifier = ConstraintMechanicsVerifier(model)
    try:
        verifier.augmented_lagrangian()
        assert False, "nonholonomic constraint must be rejected"
    except ValueError:
        pass
