"""Acceptance tests for Stage 2D Maxwell and force/energy verification."""
import sympy as sp

from automate.electromagnetism import (
    ElectromagneticField, ElectromagneticSource, ConstitutiveModel,
    ElectromagneticSystem,
)
from automate.electromagnetism.maxwell import MaxwellVerifier, LorentzForceCalculator, PoyntingVerifier


def _vacuum_plane_wave():
    # E = (0, E0 cos(kx-wt), 0), B = (0, 0, E0/c cos(kx-wt)),
    # with w = c k and mu*epsilon = 1/c^2.
    return ElectromagneticSystem(
        field=ElectromagneticField(
            electric="0,E0*cos(k*x-w*t),0",
            magnetic="0,0,E0/c*cos(k*x-w*t)",
        ),
        source=ElectromagneticSource(charge_density="0", current_density="0"),
        constitutive=ConstitutiveModel(permittivity="eps", permeability="mu"),
    )


def test_source_free_static_fields_satisfy_maxwell():
    system = ElectromagneticSystem(
        field=ElectromagneticField(electric="a*x,0,0", magnetic="0,b,0"),
        source=ElectromagneticSource(charge_density="a*eps", current_density="0"),
        constitutive=ConstitutiveModel(permittivity="eps", permeability="mu"),
    )
    passed, details, err = MaxwellVerifier(system).verify()
    assert passed, (details, err)


def test_plane_wave_requires_wave_relation():
    system = _vacuum_plane_wave()
    passed, details, _ = MaxwellVerifier(system).verify()
    assert not passed
    assert any(v != "0" for v in details["residuals"]["faraday"])


def test_lorentz_force():
    system = ElectromagneticSystem(
        field=ElectromagneticField(electric="1,0,0", magnetic="0,0,2")
    )
    force = LorentzForceCalculator(system).force("q", "0,v,0")
    q, v = sp.Symbol("q", real=True), sp.Symbol("v", real=True)\n    assert force == sp.Matrix([q * (1 + 2*v), 0, 0])


def test_poynting_theorem_for_uniform_static_fields():
    system = ElectromagneticSystem(
        field=ElectromagneticField(electric="E,0,0", magnetic="0,B,0"),
        source=ElectromagneticSource(charge_density="0", current_density="0"),
    )
    passed, details, err = PoyntingVerifier(system).verify()
    assert passed, (details, err)


def test_malformed_vector_fails_closed():
    system = ElectromagneticSystem(
        field=ElectromagneticField(electric="E,0", magnetic="0,0,B")
    )
    try:
        MaxwellVerifier(system).residuals()
        assert False, "two-component electric field must be rejected"
    except ValueError:
        pass
