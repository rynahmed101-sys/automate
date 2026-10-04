"""
EinsteinPy Cross-Validation Adapter for Automate.

Provides an independent verification oracle by computing relativistic geometric
tensors using the mature third-party library EinsteinPy (MIT license) and
comparing them against Automate's native TensorGeometry engine.

Independence Class: DIFFERENT_ENGINE
"""

from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import sympy as sp

from automate.core.sandbox import SandboxError, SandboxLimits, VerifiedExecutionSandbox

try:
    import einsteinpy
    from einsteinpy.symbolic import (
        MetricTensor,
        ChristoffelSymbols,
        RiemannCurvatureTensor,
        RicciTensor,
        RicciScalar,
        EinsteinTensor,
    )
    _EINSTEINPY_AVAILABLE = True
    _EINSTEINPY_VERSION = getattr(einsteinpy, "__version__", "0.4.0")
except ImportError:
    _EINSTEINPY_AVAILABLE = False
    _EINSTEINPY_VERSION = "Not Installed"


def is_einsteinpy_available() -> bool:
    """Returns True if einsteinpy is importable and functional."""
    return _EINSTEINPY_AVAILABLE


def get_einsteinpy_version() -> str:
    """Returns EinsteinPy version string."""
    return _EINSTEINPY_VERSION


def _cross_check_geometry_core(
    metric: sp.Matrix,
    coords: List[sp.Symbol],
    native_christoffel: Optional[Dict[Tuple[int, int, int], sp.Expr]] = None,
    native_ricci: Optional[sp.Matrix] = None,
    native_ricci_scalar: Optional[sp.Expr] = None,
    native_einstein: Optional[sp.Matrix] = None,
) -> Dict[str, Any]:
    """
    Cross-checks geometric tensors against EinsteinPy as an independent oracle.

    Parameters
    ----------
    metric : sp.Matrix
        The covariant metric tensor g_{μν}.
    coords : list of sp.Symbol
        Coordinates [x^0, x^1, ...].
    native_christoffel : dict, optional
        Automate's computed Christoffel symbols {(sigma, mu, nu): val}.
    native_ricci : sp.Matrix, optional
        Automate's computed Ricci tensor.
    native_ricci_scalar : sp.Expr, optional
        Automate's computed Ricci scalar.
    native_einstein : sp.Matrix, optional
        Automate's computed Einstein tensor.

    Returns
    -------
    dict
        Structured cross-check report with comparison results and discrepancies.
    """
    metric_payload = {
        "coordinates": [sp.srepr(coord) for coord in coords],
        "metric": sp.srepr(metric),
    }
    metric_fingerprint = hashlib.sha256(
        json.dumps(metric_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    if not _EINSTEINPY_AVAILABLE:
        return {
            "available": False,
            "engine": "EinsteinPy",
            "version": _EINSTEINPY_VERSION,
            "reason": "EinsteinPy not installed in environment",
            "all_matched": None,
            "independence_class": "NOT_RUN",
            "metric_fingerprint_sha256": metric_fingerprint,
            "comparison_method": "exact symbolic equality after SymPy simplification",
        }

    n = len(coords)
    discrepancies: List[str] = []
    checks_performed = 0

    try:
        # Construct EinsteinPy MetricTensor
        # EinsteinPy requires list of lists and tuple of coordinates
        coord_tuple = tuple(coords)
        metric_list = metric.tolist()
        ep_metric = MetricTensor(metric_list, coord_tuple)

        # 1. Christoffel cross-check
        if native_christoffel is not None:
            ep_ch = ChristoffelSymbols.from_metric(ep_metric)
            ep_ch_arr = ep_ch.tensor()
            ch_match = True
            for (sigma, mu, nu), val in native_christoffel.items():
                ep_val = ep_ch_arr[sigma, mu, nu]
                diff = sp.simplify(val - ep_val)
                if diff != 0:
                    ch_match = False
                    discrepancies.append(
                        f"Christoffel Γ^{sigma}_{{{mu}{nu}}} mismatch: Automate={val}, EinsteinPy={ep_val}, diff={diff}"
                    )
                checks_performed += 1
        else:
            ch_match = None

        # 2. Ricci Tensor cross-check
        if native_ricci is not None:
            ep_ric = RicciTensor.from_metric(ep_metric)
            ep_ric_arr = ep_ric.tensor()
            ric_match = True
            for i in range(n):
                for j in range(n):
                    ep_val = ep_ric_arr[i, j]
                    diff = sp.simplify(native_ricci[i, j] - ep_val)
                    if diff != 0:
                        ric_match = False
                        discrepancies.append(
                            f"Ricci tensor R_{{{i}{j}}} mismatch: Automate={native_ricci[i, j]}, EinsteinPy={ep_val}, diff={diff}"
                        )
                    checks_performed += 1
        else:
            ric_match = None

        # 3. Ricci Scalar cross-check
        if native_ricci_scalar is not None:
            ep_r_scalar = RicciScalar.from_metric(ep_metric)
            diff = sp.simplify(native_ricci_scalar - ep_r_scalar.expr)
            r_scalar_match = (diff == 0)
            if not r_scalar_match:
                discrepancies.append(
                    f"Ricci scalar mismatch: Automate={native_ricci_scalar}, EinsteinPy={ep_r_scalar.expr}, diff={diff}"
                )
            checks_performed += 1
        else:
            r_scalar_match = None

        # 4. Einstein Tensor cross-check
        if native_einstein is not None:
            ep_ein = EinsteinTensor.from_metric(ep_metric)
            ep_ein_arr = ep_ein.tensor()
            ein_match = True
            for i in range(n):
                for j in range(n):
                    ep_val = ep_ein_arr[i, j]
                    diff = sp.simplify(native_einstein[i, j] - ep_val)
                    if diff != 0:
                        ein_match = False
                        discrepancies.append(
                            f"Einstein tensor G_{{{i}{j}}} mismatch: Automate={native_einstein[i, j]}, EinsteinPy={ep_val}, diff={diff}"
                        )
                    checks_performed += 1
        else:
            ein_match = None

        all_matched = (len(discrepancies) == 0) and (checks_performed > 0)

        return {
            "available": True,
            "engine": "EinsteinPy",
            "version": _EINSTEINPY_VERSION,
            "license": "MIT",
            "metric_fingerprint_sha256": metric_fingerprint,
            "coordinate_representation": [sp.sstr(coord) for coord in coords],
            "metric_representation": sp.sstr(metric),
            "comparison_method": "exact symbolic equality after SymPy simplification",
            "independence_class": "DIFFERENT_ENGINE" if all_matched else "DISCREPANCY_DETECTED",
            "checks_performed": checks_performed,
            "all_matched": all_matched,
            "christoffel_matched": ch_match,
            "ricci_matched": ric_match,
            "ricci_scalar_matched": r_scalar_match,
            "einstein_matched": ein_match,
            "discrepancies": discrepancies,
        }

    except Exception as e:
        return {
            "available": True,
            "engine": "EinsteinPy",
            "version": _EINSTEINPY_VERSION,
            "error": f"EinsteinPy calculation failed: {type(e).__name__}: {str(e)}",
            "metric_fingerprint_sha256": metric_fingerprint,
            "comparison_method": "exact symbolic equality after SymPy simplification",
            "all_matched": False,
            "independence_class": "DISCREPANCY_DETECTED",
            "discrepancies": [f"Exception during EinsteinPy evaluation: {str(e)}"],
        }

    
def _geometry_metric_fingerprint(metric: sp.Matrix, coords: List[sp.Symbol]) -> str:
    """Return a deterministic fingerprint of the metric and coordinate system."""
    payload = {
        "coordinates": [sp.srepr(coord) for coord in coords],
        "metric": sp.srepr(metric),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _run_einsteinpy_cross_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn-safe worker entrypoint for the bounded EinsteinPy oracle."""
    return _cross_check_geometry_core(
        metric=payload["metric"],
        coords=payload["coords"],
        native_christoffel=payload.get("native_christoffel"),
        native_ricci=payload.get("native_ricci"),
        native_ricci_scalar=payload.get("native_ricci_scalar"),
        native_einstein=payload.get("native_einstein"),
    )


def cross_check_geometry(
    metric: sp.Matrix,
    coords: List[sp.Symbol],
    native_christoffel: Optional[Dict[Tuple[int, int, int], sp.Expr]] = None,
    native_ricci: Optional[sp.Matrix] = None,
    native_ricci_scalar: Optional[sp.Expr] = None,
    native_einstein: Optional[sp.Matrix] = None,
    sandbox_limits: Optional[SandboxLimits] = None,
) -> Dict[str, Any]:
    """
    Cross-check geometry with EinsteinPy inside VerifiedExecutionSandbox.

    The returned report records the exact metric fingerprint, external engine
    identity/version, comparison method, and the sandbox target/resource limits.
    Sandbox execution failure is distinct from a mathematical discrepancy.
    """
    metric_fingerprint = _geometry_metric_fingerprint(metric, coords)
    limits = sandbox_limits or SandboxLimits()
    payload = {
        "metric": metric,
        "coords": coords,
        "native_christoffel": native_christoffel,
        "native_ricci": native_ricci,
        "native_ricci_scalar": native_ricci_scalar,
        "native_einstein": native_einstein,
    }

    try:
        report = VerifiedExecutionSandbox(limits).run(
            "automate.tensors.einsteinpy_adapter:_run_einsteinpy_cross_check",
            payload,
        )
    except SandboxError as exc:
        return {
            "available": _EINSTEINPY_AVAILABLE,
            "engine": "EinsteinPy",
            "version": _EINSTEINPY_VERSION,
            "metric_fingerprint_sha256": metric_fingerprint,
            "comparison_method": "exact symbolic equality after SymPy simplification",
            "execution_status": "FAILED",
            "all_matched": None,
            "independence_class": "CROSS_CHECK_FAILED",
            "error": f"EinsteinPy sandbox execution failed: {type(exc).__name__}: {exc}",
            "discrepancies": [],
            "reproducibility": {
                "engine": "EinsteinPy",
                "version": _EINSTEINPY_VERSION,
                "metric_fingerprint_sha256": metric_fingerprint,
                "comparison_method": "exact symbolic equality after SymPy simplification",
                "sandbox_target": "automate.tensors.einsteinpy_adapter:_run_einsteinpy_cross_check",
                "sandbox_limits": limits.model_dump(),
            },
        }

    report["execution_status"] = "COMPLETED"
    report["sandbox"] = {
        "target": "automate.tensors.einsteinpy_adapter:_run_einsteinpy_cross_check",
        "limits": limits.model_dump(),
        "bounded_process": True,
    }
    report["reproducibility"] = {
        "engine": report.get("engine", "EinsteinPy"),
        "version": report.get("version", _EINSTEINPY_VERSION),
        "metric_fingerprint_sha256": report.get("metric_fingerprint_sha256", metric_fingerprint),
        "comparison_method": report.get(
            "comparison_method",
            "exact symbolic equality after SymPy simplification",
        ),
        "checks_performed": report.get("checks_performed", 0),
        "sandbox_target": "automate.tensors.einsteinpy_adapter:_run_einsteinpy_cross_check",
        "sandbox_limits": limits.model_dump(),
    }
    return report
