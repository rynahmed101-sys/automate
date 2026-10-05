"""Bounded numerical primitives with explicit evidence and failure semantics."""
from __future__ import annotations
from typing import Callable, Iterable, Sequence
import math, numpy as np
from scipy import optimize, integrate, interpolate, linalg

def _finite(x):
    return np.isfinite(np.asarray(x,dtype=float)).all()

def numerical_root(f: Callable[[float],float], bracket: tuple[float,float], *, xtol=1e-10) -> dict:
    a,b=map(float,bracket)
    if not a < b: raise ValueError("root bracket must satisfy a < b")
    fa,fb=float(f(a)),float(f(b))
    if not (math.isfinite(fa) and math.isfinite(fb)): raise ValueError("non-finite endpoint residual")
    if fa==0: root=a
    elif fb==0: root=b
    elif fa*fb>0: return {"status":"UNVERIFIED","reason":"bracket does not establish a sign-changing root"}
    else:
        root=float(optimize.brentq(f,a,b,xtol=xtol))
    residual=abs(float(f(root)))
    return {"status":"NUMERICALLY_CHECKED" if residual<=max(xtol,1e-12) else "UNVERIFIED",
            "root":root,"residual":residual,"method":"brentq","bracket":[a,b]}

def numerical_derivative(f: Callable[[float],float], x: float, *, h: float=1e-5) -> dict:
    if h<=0: raise ValueError("h must be positive")
    x=float(x); h=float(h)
    vals=[float(f(x-h)),float(f(x+h))]
    if not all(math.isfinite(v) for v in vals): return {"status":"UNVERIFIED","reason":"non-finite stencil evaluation"}
    value=(vals[1]-vals[0])/(2*h)
    # independent stencil refinement evidence
    h2=h/2
    fine=(float(f(x-h2))-float(f(x+h2)))/(-2*h2)
    err=abs(value-fine)
    return {"status":"NUMERICALLY_CHECKED" if err<1e-5*max(1,abs(fine)) else "UNVERIFIED",
            "value":value,"refined_value":fine,"estimated_refinement_error":err,"step":h}

def numerical_integral(f: Callable[[float],float], bounds: tuple[float,float], *, rtol=1e-8) -> dict:
    a,b=map(float,bounds)
    if not a < b: raise ValueError("integration bounds must satisfy a < b")
    val,err=integrate.quad(f,a,b,epsrel=rtol)
    if not (math.isfinite(val) and math.isfinite(err)): return {"status":"UNVERIFIED","reason":"non-finite quadrature evidence"}
    return {"status":"NUMERICALLY_CHECKED","value":float(val),"estimated_error":float(err),
            "method":"adaptive Gauss-Kronrod quadrature"}

def interpolate_linear(x: Sequence[float], y: Sequence[float], x_new: float) -> dict:
    xs=np.asarray(x,dtype=float); ys=np.asarray(y,dtype=float)
    if xs.ndim!=1 or ys.ndim!=1 or len(xs)!=len(ys) or len(xs)<2: raise ValueError("x and y must be 1-D arrays of equal length >= 2")
    if not (_finite(xs) and _finite(ys)) or np.any(np.diff(xs)<=0): raise ValueError("x must be finite and strictly increasing")
    xn=float(x_new)
    if not xs[0] <= xn <= xs[-1]: return {"status":"UNVERIFIED","reason":"extrapolation is unsupported"}
    value=float(np.interp(xn,xs,ys))
    return {"status":"NUMERICALLY_CHECKED","value":value,"method":"piecewise-linear interpolation"}

def minimize_scalar(f: Callable[[float],float], bounds: tuple[float,float]) -> dict:
    a,b=map(float,bounds)
    if not a < b: raise ValueError("optimization bounds must satisfy a < b")
    res=optimize.minimize_scalar(f,bounds=(a,b),method="bounded")
    if not res.success or not math.isfinite(float(res.fun)): return {"status":"UNVERIFIED","reason":str(res.message)}
    return {"status":"NUMERICALLY_CHECKED","x":float(res.x),"value":float(res.fun),"method":"bounded Brent"}

def eigenproblem(matrix: Sequence[Sequence[float]]) -> dict:
    A=np.asarray(matrix,dtype=float)
    if A.ndim!=2 or A.shape[0]!=A.shape[1] or A.shape[0]==0: raise ValueError("matrix must be non-empty square")
    vals,vecs=linalg.eig(A)
    residual=float(np.linalg.norm(A@vecs-vecs*vals))
    status="NUMERICALLY_CHECKED" if residual<=1e-8*max(1,float(np.linalg.norm(A))) else "UNVERIFIED"
    return {"status":status,"eigenvalues":vals.tolist(),"eigenvectors":vecs.tolist(),
            "residual_norm":residual,"method":"scipy.linalg.eig"}

def fft(samples: Sequence[complex]) -> dict:
    x=np.asarray(samples,dtype=complex)
    if x.ndim!=1 or len(x)==0: raise ValueError("FFT requires a non-empty 1-D sequence")
    y=np.fft.fft(x); recovered=np.fft.ifft(y)
    residual=float(np.max(np.abs(recovered-x)))
    return {"status":"NUMERICALLY_CHECKED" if residual<=1e-10*max(1,float(np.max(np.abs(x)))) else "UNVERIFIED",
            "spectrum":y.tolist(),"inverse_residual":residual,"method":"numpy.fft.fft"}

def monte_carlo_mean(samples: Sequence[float], *, seed: int|None=None) -> dict:
    x=np.asarray(samples,dtype=float)
    if x.ndim!=1 or len(x)<2 or not _finite(x): raise ValueError("Monte Carlo samples must be finite 1-D data with at least two values")
    mean=float(np.mean(x)); se=float(np.std(x,ddof=1)/math.sqrt(len(x)))
    return {"status":"NUMERICALLY_CHECKED","estimate":mean,"standard_error":se,"samples":int(len(x))}

def parameter_sweep(parameters: Sequence[float], evaluator: Callable[[float],float]) -> dict:
    p=np.asarray(parameters,dtype=float)
    if p.ndim!=1 or len(p)==0 or not _finite(p): raise ValueError("sweep parameters must be finite non-empty 1-D data")
    vals=[float(evaluator(float(v))) for v in p]
    if not _finite(vals): return {"status":"UNVERIFIED","reason":"non-finite sweep result"}
    return {"status":"NUMERICALLY_CHECKED","parameters":p.tolist(),"values":vals}

