"""Evidence-oriented numerical mathematics primitives.

All successful results are numerical evidence, not symbolic proof.  Inputs are
validated, unsupported extrapolation/semantics fail closed, and residual or
refinement evidence is returned with the numerical result.
"""
from __future__ import annotations

from typing import Callable, Sequence
import math

import numpy as np
from scipy import integrate, linalg, optimize


def _finite(x) -> bool:
    return bool(np.isfinite(np.asarray(x, dtype=float)).all())


def _checked_residual(residual: float, scale: float = 1.0, tolerance: float = 1e-8) -> str:
    if not math.isfinite(float(residual)):
        return "UNVERIFIED"
    return "NUMERICALLY_CHECKED" if float(residual) <= tolerance * max(1.0, abs(float(scale))) else "UNVERIFIED"


def numerical_root(
    f: Callable[[float], float],
    bracket: tuple[float, float],
    *,
    xtol: float = 1e-10,
) -> dict:
    a, b = map(float, bracket)
    if not a < b:
        raise ValueError("root bracket must satisfy a < b")
    if xtol <= 0:
        raise ValueError("xtol must be positive")
    fa, fb = float(f(a)), float(f(b))
    if not (math.isfinite(fa) and math.isfinite(fb)):
        raise ValueError("non-finite endpoint residual")
    if fa == 0:
        root = a
    elif fb == 0:
        root = b
    elif fa * fb > 0:
        return {"status": "UNVERIFIED", "reason": "bracket does not establish a sign-changing root"}
    else:
        root = float(optimize.brentq(f, a, b, xtol=xtol))
    residual = abs(float(f(root)))
    return {
        "status": _checked_residual(residual, tolerance=max(xtol, 1e-12)),
        "root": root,
        "residual": residual,
        "method": "brentq",
        "bracket": [a, b],
    }


def numerical_nonlinear_system(
    functions: Sequence[Callable[[np.ndarray], float]],
    initial_guess: Sequence[float],
    *,
    xtol: float = 1e-10,
) -> dict:
    """Solve F(x)=0 with explicit residual evidence.

    The initial guess is not proof of existence or uniqueness; solver success
    and an independently evaluated residual determine the status.
    """
    x0 = np.asarray(initial_guess, dtype=float)
    if x0.ndim != 1 or len(x0) == 0 or not _finite(x0):
        raise ValueError("initial_guess must be a finite non-empty 1-D sequence")
    if len(functions) != len(x0):
        raise ValueError("number of equations must equal number of unknowns")
    if xtol <= 0:
        raise ValueError("xtol must be positive")

    def residual_fn(x):
        vals = np.asarray([float(fn(np.asarray(x, dtype=float))) for fn in functions], dtype=float)
        return vals

    result = optimize.root(residual_fn, x0, method="hybr", options={"xtol": xtol})
    residual_vector = residual_fn(result.x)
    residual_norm = float(np.linalg.norm(residual_vector))
    status = "NUMERICALLY_CHECKED" if result.success and residual_norm <= max(xtol, 1e-12) else "UNVERIFIED"
    return {
        "status": status,
        "solution": result.x.tolist(),
        "residual_vector": residual_vector.tolist(),
        "residual_norm": residual_norm,
        "solver_success": bool(result.success),
        "message": str(result.message),
        "method": "scipy.optimize.root(hybr)",
    }


def numerical_derivative(
    f: Callable[[float], float],
    x: float,
    *,
    h: float = 1e-5,
) -> dict:
    if h <= 0:
        raise ValueError("h must be positive")
    x, h = float(x), float(h)
    left, right = float(f(x - h)), float(f(x + h))
    if not all(math.isfinite(v) for v in (left, right)):
        return {"status": "UNVERIFIED", "reason": "non-finite stencil evaluation"}
    value = (right - left) / (2 * h)
    h2 = h / 2
    fine = (float(f(x + h2)) - float(f(x - h2))) / (2 * h2)
    err = abs(value - fine)
    return {
        "status": "NUMERICALLY_CHECKED" if err < 1e-5 * max(1, abs(fine)) else "UNVERIFIED",
        "value": value,
        "refined_value": fine,
        "estimated_refinement_error": err,
        "step": h,
    }


def numerical_integral(
    f: Callable[[float], float],
    bounds: tuple[float, float],
    *,
    rtol: float = 1e-8,
) -> dict:
    a, b = map(float, bounds)
    if not a < b:
        raise ValueError("integration bounds must satisfy a < b")
    if rtol <= 0:
        raise ValueError("rtol must be positive")
    val, err = integrate.quad(f, a, b, epsrel=rtol)
    if not (math.isfinite(val) and math.isfinite(err)):
        return {"status": "UNVERIFIED", "reason": "non-finite quadrature evidence"}
    return {
        "status": "NUMERICALLY_CHECKED",
        "value": float(val),
        "estimated_error": float(err),
        "method": "adaptive Gauss-Kronrod quadrature",
    }


def interpolate_linear(x: Sequence[float], y: Sequence[float], x_new: float) -> dict:
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if xs.ndim != 1 or ys.ndim != 1 or len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("x and y must be 1-D arrays of equal length >= 2")
    if not (_finite(xs) and _finite(ys)) or np.any(np.diff(xs) <= 0):
        raise ValueError("x must be finite and strictly increasing")
    xn = float(x_new)
    if not xs[0] <= xn <= xs[-1]:
        return {"status": "UNVERIFIED", "reason": "extrapolation is unsupported"}
    value = float(np.interp(xn, xs, ys))
    return {"status": "NUMERICALLY_CHECKED", "value": value, "method": "piecewise-linear interpolation"}


def minimize_scalar(f: Callable[[float], float], bounds: tuple[float, float]) -> dict:
    a, b = map(float, bounds)
    if not a < b:
        raise ValueError("optimization bounds must satisfy a < b")
    res = optimize.minimize_scalar(f, bounds=(a, b), method="bounded")
    if not res.success or not math.isfinite(float(res.fun)):
        return {"status": "UNVERIFIED", "reason": str(res.message)}
    return {
        "status": "NUMERICALLY_CHECKED",
        "x": float(res.x),
        "value": float(res.fun),
        "method": "bounded Brent",
    }


def numerical_linear_solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float]) -> dict:
    A = np.asarray(matrix, dtype=float)
    b = np.asarray(rhs, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or A.shape[0] == 0:
        raise ValueError("matrix must be non-empty square")
    if b.ndim != 1 or len(b) != A.shape[0] or not (_finite(A) and _finite(b)):
        raise ValueError("rhs must be finite and match the square matrix dimension")
    try:
        x = linalg.solve(A, b)
    except linalg.LinAlgError as exc:
        return {"status": "UNVERIFIED", "reason": f"linear solve failed: {exc}"}
    residual = float(np.linalg.norm(A @ x - b))
    return {
        "status": _checked_residual(residual, np.linalg.norm(b)),
        "solution": x.tolist(),
        "residual_norm": residual,
        "condition_number_2": float(np.linalg.cond(A)),
        "method": "scipy.linalg.solve",
    }


def eigenproblem(matrix: Sequence[Sequence[float]]) -> dict:
    A = np.asarray(matrix, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or A.shape[0] == 0:
        raise ValueError("matrix must be non-empty square")
    vals, vecs = linalg.eig(A)
    residual = float(np.linalg.norm(A @ vecs - vecs * vals))
    status = "NUMERICALLY_CHECKED" if residual <= 1e-8 * max(1, float(np.linalg.norm(A))) else "UNVERIFIED"
    return {
        "status": status,
        "eigenvalues": vals.tolist(),
        "eigenvectors": vecs.tolist(),
        "residual_norm": residual,
        "method": "scipy.linalg.eig",
    }


def condition_number(matrix: Sequence[Sequence[float]]) -> dict:
    A = np.asarray(matrix, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or A.shape[0] == 0 or not _finite(A):
        raise ValueError("matrix must be a finite non-empty square matrix")
    cond = float(np.linalg.cond(A))
    return {
        "status": "NUMERICALLY_CHECKED" if math.isfinite(cond) else "UNVERIFIED",
        "condition_number_2": cond,
        "interpretation": "large condition number indicates potential sensitivity; no universal cutoff is inferred",
    }


def sensitivity_finite_difference(
    f: Callable[[float], float],
    x: float,
    *,
    h: float = 1e-5,
) -> dict:
    x = float(x)
    if h <= 0:
        raise ValueError("h must be positive")
    fm, fp = float(f(x - h)), float(f(x + h))
    if not all(math.isfinite(v) for v in (fm, fp)):
        return {"status": "UNVERIFIED", "reason": "non-finite sensitivity stencil"}
    derivative = (fp - fm) / (2 * h)
    center = float(f(x))
    relative = None if center == 0 or x == 0 else abs((x / center) * derivative)
    return {
        "status": "NUMERICALLY_CHECKED",
        "derivative": derivative,
        "relative_sensitivity": relative,
        "step": h,
    }


def propagate_uncertainty(
    function: Callable[[np.ndarray], float],
    means: Sequence[float],
    standard_deviations: Sequence[float],
    *,
    relative_step: float = 1e-5,
) -> dict:
    mu = np.asarray(means, dtype=float)
    sigma = np.asarray(standard_deviations, dtype=float)
    if mu.ndim != 1 or sigma.ndim != 1 or len(mu) == 0 or len(mu) != len(sigma):
        raise ValueError("means and standard_deviations must be equal-length non-empty 1-D sequences")
    if not (_finite(mu) and _finite(sigma)) or np.any(sigma < 0) or relative_step <= 0:
        raise ValueError("means/sigmas must be finite with non-negative sigmas")
    f0 = float(function(mu))
    gradients = []
    for i in range(len(mu)):
        h = relative_step * max(1.0, abs(mu[i]))
        plus, minus = mu.copy(), mu.copy()
        plus[i] += h
        minus[i] -= h
        gradients.append((float(function(plus)) - float(function(minus))) / (2 * h))
    gradients = np.asarray(gradients, dtype=float)
    variance = float(np.sum((gradients * sigma) ** 2))
    return {
        "status": "NUMERICALLY_CHECKED" if _finite(gradients) else "UNVERIFIED",
        "estimate": f0,
        "standard_uncertainty": math.sqrt(max(0.0, variance)),
        "gradients": gradients.tolist(),
        "assumption": "first-order propagation with independent input uncertainties; covariance is not modeled",
    }


def convergence_evidence(approximations: Sequence[float]) -> dict:
    values = np.asarray(approximations, dtype=float)
    if values.ndim != 1 or len(values) < 3 or not _finite(values):
        raise ValueError("at least three finite approximations are required")
    differences = np.abs(np.diff(values))
    ratios = np.divide(
        differences[1:],
        differences[:-1],
        out=np.full(len(differences) - 1, np.nan),
        where=differences[:-1] != 0,
    )
    decreasing = bool(differences[-1] < differences[0] and np.all(np.diff(differences) <= 0))
    return {
        "status": "NUMERICALLY_CHECKED" if decreasing else "UNVERIFIED",
        "approximations": values.tolist(),
        "successive_differences": differences.tolist(),
        "successive_error_ratios": ratios.tolist(),
        "interpretation": "empirical convergence evidence only; no convergence theorem is established",
    }


def numerical_pde_1d_dirichlet(
    source: Callable[[float], float],
    domain: tuple[float, float],
    boundary_values: tuple[float, float],
    *,
    interior_points: int = 32,
) -> dict:
    """Solve -u''(x)=f(x) on a finite interval with Dirichlet endpoints.

    The returned residual is evaluated from the same finite-difference stencil
    used to construct the linear system; it is numerical evidence for the
    discretized problem, not a proof for the continuous PDE.
    """
    left, right = map(float, domain)
    u_left, u_right = map(float, boundary_values)
    if not left < right or interior_points < 1:
        raise ValueError("domain must be ordered and interior_points must be positive")
    n = int(interior_points)
    grid = np.linspace(left, right, n + 2)
    h = float(grid[1] - grid[0])
    interior = grid[1:-1]
    rhs = np.asarray([float(source(x)) for x in interior], dtype=float)
    if not _finite(rhs):
        return {"status": "UNVERIFIED", "reason": "non-finite source evaluation"}
    main = 2.0 * np.ones(n)
    off = -1.0 * np.ones(n - 1)
    matrix = (np.diag(main) + np.diag(off, 1) + np.diag(off, -1)) / h**2
    rhs = rhs.copy()
    rhs[0] += u_left / h**2
    rhs[-1] += u_right / h**2
    solution = np.asarray(linalg.solve(matrix, rhs), dtype=float)
    full = np.concatenate(([u_left], solution, [u_right]))
    discrete_residual = matrix @ solution - (
        np.asarray([float(source(x)) for x in interior], dtype=float)
        + np.eye(n)[0] * u_left / h**2
        + np.eye(n)[-1] * u_right / h**2
    )
    residual_norm = float(np.linalg.norm(discrete_residual))
    return {
        "status": _checked_residual(residual_norm, np.linalg.norm(rhs)),
        "grid": grid.tolist(),
        "solution": full.tolist(),
        "discrete_residual_norm": residual_norm,
        "step": h,
        "method": "second-order centered finite difference",
        "interpretation": "evidence for the discretized boundary-value problem, not continuous-PDE proof",
    }


def fft(samples: Sequence[complex]) -> dict:
    x = np.asarray(samples, dtype=complex)
    if x.ndim != 1 or len(x) == 0:
        raise ValueError("FFT requires a non-empty 1-D sequence")
    y = np.fft.fft(x)
    recovered = np.fft.ifft(y)
    residual = float(np.max(np.abs(recovered - x)))
    return {
        "status": "NUMERICALLY_CHECKED" if residual <= 1e-10 * max(1, float(np.max(np.abs(x)))) else "UNVERIFIED",
        "spectrum": y.tolist(),
        "inverse_residual": residual,
        "method": "numpy.fft.fft",
    }


def monte_carlo_mean(samples: Sequence[float], *, seed: int | None = None) -> dict:
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not _finite(x):
        raise ValueError("Monte Carlo samples must be finite 1-D data with at least two values")
    mean = float(np.mean(x))
    se = float(np.std(x, ddof=1) / math.sqrt(len(x)))
    return {
        "status": "NUMERICALLY_CHECKED",
        "estimate": mean,
        "standard_error": se,
        "samples": int(len(x)),
        "seed": seed,
        "interpretation": "sample-based uncertainty; convergence/distribution assumptions are not inferred",
    }


def parameter_sweep(parameters: Sequence[float], evaluator: Callable[[float], float]) -> dict:
    p = np.asarray(parameters, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not _finite(p):
        raise ValueError("sweep parameters must be finite non-empty 1-D data")
    vals = [float(evaluator(float(v))) for v in p]
    if not _finite(vals):
        return {"status": "UNVERIFIED", "reason": "non-finite sweep result"}
    return {"status": "NUMERICALLY_CHECKED", "parameters": p.tolist(), "values": vals}
