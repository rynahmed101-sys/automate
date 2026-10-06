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


def test_nonlinear_system_linear_solve_and_conditioning():
    from automate.numerical import (
        numerical_nonlinear_system, numerical_linear_solve, condition_number,
    )
    system = numerical_nonlinear_system(
        [lambda z: z[0] ** 2 + z[1] - 3.0, lambda z: z[0] + z[1] ** 2 - 3.0],
        [1.0, 1.0],
    )
    assert system["status"] == "NUMERICALLY_CHECKED"
    assert system["residual_norm"] < 1e-8

    solved = numerical_linear_solve([[3.0, 1.0], [1.0, 2.0]], [5.0, 5.0])
    assert solved["status"] == "NUMERICALLY_CHECKED"
    assert solved["residual_norm"] < 1e-8
    assert condition_number([[3.0, 1.0], [1.0, 2.0]])["condition_number_2"] >= 1.0


def test_sensitivity_uncertainty_and_convergence_evidence():
    from automate.numerical import sensitivity_finite_difference, propagate_uncertainty, convergence_evidence
    sensitivity = sensitivity_finite_difference(lambda x: x * x, 2.0)
    assert sensitivity["status"] == "NUMERICALLY_CHECKED"
    assert abs(sensitivity["derivative"] - 4.0) < 1e-6

    uncertainty = propagate_uncertainty(
        lambda z: z[0] + 2.0 * z[1],
        [3.0, 4.0],
        [0.1, 0.2],
    )
    assert uncertainty["status"] == "NUMERICALLY_CHECKED"
    assert abs(uncertainty["standard_uncertainty"] - (0.17 ** 0.5)) < 1e-8

    convergence = convergence_evidence([1.0, 0.5, 0.25, 0.125])
    assert convergence["status"] == "NUMERICALLY_CHECKED"


def test_numerical_pde_dirichlet_has_discrete_residual():
    from automate.numerical import numerical_pde_1d_dirichlet
    result = numerical_pde_1d_dirichlet(
        lambda x: 2.0,
        (0.0, 1.0),
        (0.0, 0.0),
        interior_points=8,
    )
    assert result["status"] == "NUMERICALLY_CHECKED"
    assert result["discrete_residual_norm"] < 1e-8
