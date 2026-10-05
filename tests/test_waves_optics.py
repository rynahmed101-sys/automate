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
