import math
import pytest
from automate.waves_optics import *
def test_harmonic_wave_and_superposition():
    w=HarmonicWave(2,4,3,0,1)
    assert w.value(0,0)==pytest.approx(2)
    s=superpose([HarmonicWave(1,4,3,0),HarmonicWave(1,4,3,math.pi)])
    assert s.amplitude==pytest.approx(0)
def test_superposition_rejects_incompatible_waves():
    with pytest.raises(ValueError): superpose([HarmonicWave(1,2,1),HarmonicWave(1,3,1)])
def test_standing_wave_structure():
    import sympy as sp
    x,t=sp.symbols("x t", real=True)
    expr=standing_wave(2,4,3)
    assert sp.simplify(expr.subs({x:0,t:0})-4)==0
def test_dispersion_and_refraction_boundary():
    assert dispersion_relation(6,2)["phase_velocity"]==3
    r=ReflectionRefraction(1.5,1,math.asin(0.5))
    assert r.refracted_angle()==pytest.approx(math.asin(0.75))
    with pytest.raises(ValueError): ReflectionRefraction(1.5,1,math.asin(0.9)).refracted_angle()
def test_polarization_normalization():
    p=PolarizationState(1+1j,1j).normalized()
    assert p.intensity()==pytest.approx(1)
    with pytest.raises(ValueError): PolarizationState(0j,0j).normalized()
def test_diffraction():
    assert diffraction_single_slit(1,2,0)["relative_intensity"]==pytest.approx(1)
    assert diffraction_single_slit(1,2,math.asin(.5))["relative_intensity"]==pytest.approx((math.sin(math.pi)/math.pi)**2)


def test_interference_and_wave_equation_evidence():
    from automate.waves_optics import interference_intensity, verify_harmonic_wave_equation
    w1 = HarmonicWave(1.0, 2.0, 1.0, 0.0)
    w2 = HarmonicWave(1.0, 2.0, 1.0, 3.141592653589793)
    result = interference_intensity(w1, w2, 0.0, 0.0)
    assert result["status"] == "NUMERICALLY_CHECKED"
    assert abs(result["relative_intensity"]) < 1e-20

    checked = verify_harmonic_wave_equation(w1, 2.0)
    assert checked["status"] == "SYMBOLIC_CHECKED"
    assert checked["residual_amplitude"] == 0.0


def test_dispersion_fresnel_and_stokes():
    from automate.waves_optics import dispersion_curve, ReflectionRefraction, PolarizationState
    curve = dispersion_curve(lambda k: 3.0 * k, [1.0, 2.0, 3.0])
    assert curve["status"] == "NUMERICALLY_CHECKED"
    assert all(abs(v - 3.0) < 1e-6 for v in curve["group_velocities"])

    optics = ReflectionRefraction(1.0, 1.5, 0.3)
    fresnel = optics.fresnel_reflectance()
    assert fresnel["status"] == "NUMERICALLY_CHECKED"
    assert 0.0 <= fresnel["reflectance_s"] <= 1.0
    assert 0.0 <= fresnel["reflectance_p"] <= 1.0

    stokes = PolarizationState(1.0 + 0j, 1.0j).stokes()
    assert stokes["status"] == "NUMERICALLY_CHECKED"
    assert abs(stokes["I"] - 1.0) < 1e-12
    assert abs(stokes["V"] - 1.0) < 1e-12
