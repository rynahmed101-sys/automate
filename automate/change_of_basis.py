"""Isolated change-of-basis semantics for Stage 1A.

This module deliberately avoids central rule registration. It provides a
reviewable mathematical primitive that the primary integration pass can expose
through shared contracts after reconciliation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import sympy as sp
from automate.ir.linear_algebra import LinearAlgebraParseError, parse_linear_algebra_expression

@dataclass(frozen=True)
class ChangeOfBasisResult:
    status: str
    coordinates: tuple[str, ...] | None
    reconstructed_vector: tuple[str, ...] | None
    residual: tuple[str, ...] | None
    matrix_shape: tuple[int, int] | None
    numpy_cross_check: dict[str, Any]
    error: str | None = None

def _vector_strings(v: sp.MatrixBase) -> tuple[str, ...]:
    return tuple(str(sp.simplify(v[i,0])) for i in range(v.rows))

def _zero_state(expr: sp.Expr) -> bool | None:
    try: reduced=sp.simplify(expr)
    except Exception: return None
    if reduced == 0 or reduced.is_zero is True: return True
    if reduced.is_zero is False: return False
    try: result=reduced.equals(0)
    except Exception: result=None
    return True if result is True else None

def _matrix_zero_state(m: sp.MatrixBase) -> bool | None:
    states=[_zero_state(v) for v in m]
    if any(s is False for s in states): return False
    if all(s is True for s in states): return True
    return None

def _numeric_vector(v: sp.MatrixBase) -> np.ndarray | None:
    out=[]
    for x in v:
        if not x.is_number: return None
        try: z=complex(sp.N(x,16))
        except Exception: return None
        out.append(float(z.real) if abs(z.imag)<1e-14 else z)
    return np.asarray(out)

def _numeric_matrix(m: sp.MatrixBase) -> np.ndarray | None:
    out=[]
    for i in range(m.rows):
        row=[]
        for j in range(m.cols):
            x=m[i,j]
            if not x.is_number: return None
            try: z=complex(sp.N(x,16))
            except Exception: return None
            row.append(float(z.real) if abs(z.imag)<1e-14 else z)
        out.append(row)
    return np.asarray(out)

def coordinates_in_basis(basis_text: str, vector_text: str, *, rtol: float=1e-9, atol: float=1e-10) -> ChangeOfBasisResult:
    """Express a vector in an ordered full-dimensional basis.

    Basis vectors are columns of B. Returned coordinates c satisfy B*c=x.
    """
    try:
        bp=parse_linear_algebra_expression(basis_text)
        vp=parse_linear_algebra_expression(vector_text)
    except LinearAlgebraParseError as exc:
        return ChangeOfBasisResult("FAILED",None,None,None,None,{"available":False,"independence_class":"NOT_AVAILABLE"},f"Invalid expression: {exc}")
    if bp.kind!="matrix" or vp.kind!="vector":
        return ChangeOfBasisResult("FAILED",None,None,None,None,{"available":False,"independence_class":"NOT_APPLICABLE"},"Requires a matrix basis and a vector.")
    B=sp.Matrix(bp.value); x=sp.Matrix(vp.value); shape=(int(B.rows),int(B.cols))
    if B.rows!=B.cols:
        return ChangeOfBasisResult("FAILED",None,None,None,shape,{"available":False,"independence_class":"NOT_APPLICABLE"},f"Basis matrix must be square; received {shape}.")
    if x.rows!=B.rows:
        return ChangeOfBasisResult("FAILED",None,None,None,shape,{"available":False,"independence_class":"NOT_APPLICABLE"},f"Vector dimension {x.rows} does not match basis dimension {B.rows}.")
    ds=_zero_state(sp.simplify(B.det()))
    if ds is True:
        return ChangeOfBasisResult("FAILED",None,None,None,shape,{"available":False,"independence_class":"NOT_APPLICABLE"},"The supplied basis matrix is singular.")
    if ds is None:
        return ChangeOfBasisResult("UNVERIFIED",None,None,None,shape,{"available":False,"independence_class":"NOT_AVAILABLE"},"Basis independence cannot be established symbolically.")
    try: c=sp.simplify(B.inv()*x)
    except (ValueError,sp.NonSquareMatrixError,sp.MatrixError) as exc:
        return ChangeOfBasisResult("FAILED",None,None,None,shape,{"available":False,"independence_class":"NOT_AVAILABLE"},f"Coordinate conversion failed: {type(exc).__name__}: {exc}")
    recon=sp.simplify(B*c); residual=sp.simplify(recon-x); rs=_matrix_zero_state(residual)
    if rs is not True:
        return ChangeOfBasisResult("FAILED" if rs is False else "UNVERIFIED",_vector_strings(c),_vector_strings(recon),_vector_strings(residual),shape,{"available":False,"independence_class":"NOT_AVAILABLE"},"Reconstruction identity could not be established exactly.")
    nb,nx=_numeric_matrix(B),_numeric_vector(x)
    if nb is None or nx is None:
        cross={"available":False,"independence_class":"NOT_AVAILABLE"}
    else:
        try:
            nc=np.linalg.solve(nb,nx); nr=nb@nc-nx
            cross={"available":True,"independence_class":"DIFFERENT_ENGINE","engine":"numpy.linalg.solve","passed":bool(np.allclose(nb@nc,nx,rtol=rtol,atol=atol,equal_nan=False)),"residual_norm_2":float(np.linalg.norm(nr)),"rtol":rtol,"atol":atol}
        except (TypeError,ValueError,np.linalg.LinAlgError) as exc:
            cross={"available":False,"independence_class":"NOT_AVAILABLE","reason":f"NumPy cross-check unavailable: {type(exc).__name__}: {exc}"}
    return ChangeOfBasisResult("SYMBOLIC_CHECKED",_vector_strings(c),_vector_strings(recon),_vector_strings(residual),shape,cross)

def verify_basis_matrix(basis_text: str) -> dict[str,Any]:
    try: p=parse_linear_algebra_expression(basis_text)
    except LinearAlgebraParseError as exc: return {"status":"FAILED","error":f"Invalid basis expression: {exc}"}
    if p.kind!="matrix": return {"status":"FAILED","error":"Basis must be represented by a matrix."}
    B=sp.Matrix(p.value)
    if B.rows!=B.cols: return {"status":"FAILED","shape":[int(B.rows),int(B.cols)],"error":"Basis matrix must be square for this API."}
    d=sp.simplify(B.det()); s=_zero_state(d)
    if s is False: return {"status":"SYMBOLIC_CHECKED","independent":True,"determinant":str(d)}
    if s is True: return {"status":"FAILED","independent":False,"determinant":"0"}
    return {"status":"UNVERIFIED","independent":None,"determinant":str(d),"error":"Symbolic determinant non-zeroness cannot be established."}
