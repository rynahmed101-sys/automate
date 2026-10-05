"""Acceptance tests for reusable Stage 2C classical-mechanics representations."""
import sympy as sp
import pytest
from automate.mechanics import (
    GeneralizedCoordinate, GeneralizedForce, MechanicalConstraint,
    MechanicalSystemRepresentation,
)
def test_representation_composes_into_lagrangian_system():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x", dimension="L")],
        kinetic_energy="m*x_dot**2/2", potential_energy="k*x**2/2",
        parameters={"m": "positive", "k": "positive"})
    assert sp.simplify(model.lagrangian() - model.parse("m*x_dot**2/2 - k*x**2/2")) == 0
    system = model.as_lagrangian_system()
    passed, _, _, err = system.verify_euler_lagrange("m*x_ddot + k*x")
    assert passed, err
def test_kinematics_are_representation_level():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="q1"), GeneralizedCoordinate(name="q2")],
        kinetic_energy="m*(q1_dot**2+q2_dot**2)/2", parameters={"m": "positive"})
    assert [k.coordinate for k in model.kinematics()] == ["q1", "q2"]
    assert model.kinematics()[0].velocity == "d(q1)/dt"
def test_constraints_and_forces_are_explicit():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")], kinetic_energy="m*x_dot**2/2",
        forces=[GeneralizedForce(coordinate="x", expression="F")],
        constraints=[MechanicalConstraint(expression="x-L")])
    assert model.generalized_force_map()["x"] == sp.Symbol("F", real=True)
    assert model.constraint_residuals()["x-L"] == sp.Symbol("x", real=True) - sp.Symbol("L", real=True)
def test_unknown_force_coordinate_fails_closed():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")], kinetic_energy="m*x_dot**2/2",
        forces=[GeneralizedForce(coordinate="y", expression="F")])
    with pytest.raises(ValueError, match="unknown generalized coordinate"):
        model.generalized_force_map()
def test_bad_constraint_is_not_silently_satisfied():
    model = MechanicalSystemRepresentation(
        coordinates=[GeneralizedCoordinate(name="x")], kinetic_energy="m*x_dot**2/2",
        constraints=[MechanicalConstraint(expression="x-1")])
    assert model.constraint_residuals()["x-1"] != 0
