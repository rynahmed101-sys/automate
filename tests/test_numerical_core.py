import math, numpy as np, pytest
from automate.numerical import *
def test_root_requires_bracket_and_checks_residual():
    r=numerical_root(lambda x:x*x-2,(0,2)); assert r["status"]=="NUMERICALLY_CHECKED"; assert r["residual"]<1e-9
    assert numerical_root(lambda x:x*x+1,(0,2))["status"]=="UNVERIFIED"
def test_derivative_refinement():
    r=numerical_derivative(lambda x:x*x,2); assert r["value"]==pytest.approx(4,rel=1e-5)
def test_integral():
    r=numerical_integral(math.sin,(0,math.pi)); assert r["value"]==pytest.approx(2,rel=1e-8)
def test_interpolation_rejects_extrapolation():
    assert interpolate_linear([0,1],[0,1],.5)["value"]==pytest.approx(.5)
    assert interpolate_linear([0,1],[0,1],2)["status"]=="UNVERIFIED"
def test_optimization_and_eigen_residual():
    r=minimize_scalar(lambda x:(x-2)**2,(0,4)); assert r["x"]==pytest.approx(2,abs=1e-5)
    e=eigenproblem([[2,0],[0,3]]); assert e["status"]=="NUMERICALLY_CHECKED"
def test_fft_round_trip_and_mc():
    assert fft([1,2,3,4])["status"]=="NUMERICALLY_CHECKED"
    assert monte_carlo_mean([1,2,3],seed=7)["estimate"]==2
def test_sweep_malformed():
    with pytest.raises(ValueError): parameter_sweep([],lambda x:x)
