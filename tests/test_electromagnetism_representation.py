"""Acceptance tests for reusable Stage 2D electromagnetism representations."""
import pytest
from automate.electromagnetism import (ElectromagneticField, ElectromagneticSource,
    ElectromagneticPotentials, ConstitutiveModel, ElectromagneticSystem)

def test_field_source_potential_representation():
    system = ElectromagneticSystem(
        field=ElectromagneticField(electric="E", magnetic="B"),
        source=ElectromagneticSource(charge_density="rho", current_density="J"),
        potentials=ElectromagneticPotentials(scalar_potential="phi", vector_potential="A", gauge="Lorenz"))
    assert system.has_dynamic_sources()
    assert system.has_potentials()
    assert system.constitutive.electric_relation == "D = epsilon*E"

def test_source_free_system_is_explicit():
    system = ElectromagneticSystem(field=ElectromagneticField(electric="E", magnetic="B"))
    assert not system.has_dynamic_sources()

def test_invalid_extra_structure_is_rejected():
    with pytest.raises(Exception):
        ElectromagneticField(electric="E", magnetic="B", unexpected="x")

def test_constitutive_metadata_is_explicit():
    model = ConstitutiveModel(permittivity="epsilon_r*epsilon0", permeability="mu_r*mu0")
    assert model.permittivity == "epsilon_r*epsilon0"
    assert model.permeability == "mu_r*mu0"