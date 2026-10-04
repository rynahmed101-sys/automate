"""
Automate Tensor Verification Backend (TensorChecker).

Orchestrates component-level geometric tensor verification:
  - Metric Tensor validation
  - Christoffel Symbols: Γ^σ_{μν}
  - Riemann Curvature Tensor: R^σ_{ρμν}
  - Ricci Curvature Tensor: R_{μν}
  - Ricci Curvature Scalar: R
  - Einstein Tensor: G_{μν}
  - Geodesic Equations of Motion
  - Index Contraction / Raising / Lowering

Orchestrates multi-engine cross-validation using EinsteinPy as an independent oracle
and tags results with their explicit independence_class (DIFFERENT_ENGINE vs SAME_ENGINE).
"""

import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
import sympy as sp

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph
from automate.ir.safe_parser import SafeParser, SafeParseError
from automate.tensors.algebra import TensorGeometry
from automate.tensors.einsteinpy_adapter import (
    cross_check_geometry,
    is_einsteinpy_available,
    get_einsteinpy_version,
)

_SUPPORTED_TENSOR_RULES = frozenset({
    "christoffel_symbols",
    "riemann_curvature",
    "ricci_curvature",
    "ricci_scalar",
    "einstein_tensor",
    "geodesic_equations",
    "index_contract",
    "raise_index",
    "lower_index",
})


class TensorChecker(BaseChecker):
    """
    Symbolic tensor and differential geometry verification backend.
    """

    def __init__(self):
        self._name = "TensorChecker"
        self._ep_available = is_einsteinpy_available()
        self._ep_version = get_einsteinpy_version()

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        v = f"SymPy {sp.__version__}"
        if self._ep_available:
            v += f" + EinsteinPy {self._ep_version}"
        return v

    def is_available(self) -> bool:
        return True

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start_time = time.perf_counter()
        rule = edge.transformation_rule

        # 1. Rule applicability check
        if rule not in _SUPPORTED_TENSOR_RULES:
            elapsed = (time.perf_counter() - start_time) * 1000
            return VerificationReport(
                status=VerificationStatus.NOT_APPLICABLE,
                backend=self.name,
                backend_version=self.version,
                execution_time_ms=elapsed,
                passed=False,
                details={
                    "rule": rule,
                    "reason": f"Rule '{rule}' is not supported by TensorChecker. Supported: {', '.join(sorted(_SUPPORTED_TENSOR_RULES))}"
                },
                error_message=f"Rule '{rule}' is NOT_APPLICABLE for TensorChecker."
            )

        # 2. Node resolution
        in_nodes = [graph.get_node(nid) for nid in edge.input_nodes]
        out_nodes = [graph.get_node(nid) for nid in edge.output_nodes]

        if not all(in_nodes) or not all(out_nodes) or len(in_nodes) == 0 or len(out_nodes) == 0:
            elapsed = (time.perf_counter() - start_time) * 1000
            return VerificationReport(
                status=VerificationStatus.FAILED,
                backend=self.name,
                backend_version=self.version,
                execution_time_ms=elapsed,
                passed=False,
                error_message="Missing required input or output derivation nodes."
            )

        # 3. Side conditions check
        active_asms = {aid for aid, a in graph.assumptions.items() if a.active}
        if edge.side_conditions:
            valid_conds, missing_conds = edge.validate_side_conditions(active_asms)
            if not valid_conds:
                elapsed = (time.perf_counter() - start_time) * 1000
                return VerificationReport(
                    status=VerificationStatus.CONDITIONAL,
                    backend=self.name,
                    backend_version=self.version,
                    execution_time_ms=elapsed,
                    passed=False,
                    details={"missing_side_conditions": missing_conds},
                    error_message=f"Missing required side conditions: {', '.join(missing_conds)}"
                )

        params = edge.parameters or {}

        # 4. Extract and construct metric tensor
        try:
            tg, metric_matrix, coord_syms = self._build_tensor_geometry(in_nodes[0], params)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            return VerificationReport(
                status=VerificationStatus.FAILED,
                backend=self.name,
                backend_version=self.version,
                execution_time_ms=elapsed,
                passed=False,
                error_message=f"Failed to construct TensorGeometry: {type(e).__name__}: {str(e)}"
            )

        # 5. Rule execution and comparison
        passed = False
        details: Dict[str, Any] = {}
        error_msg: Optional[str] = None
        independence_class = "SAME_ENGINE"

        try:
            out_node = out_nodes[0]
            claim_str = out_node.expression.raw_str.strip()

            if rule == "ricci_scalar":
                actual_R = tg.ricci_scalar()
                # Parse claimed scalar
                parser = SafeParser(extra_symbols={str(s): s for s in coord_syms})
                claimed_R = parser.parse(claim_str)
                diff = sp.simplify(actual_R - claimed_R)
                passed = (diff == 0)
                details = {
                    "rule": rule,
                    "actual_ricci_scalar": str(actual_R),
                    "claimed_ricci_scalar": str(claimed_R),
                    "diff": str(diff),
                }
                if not passed:
                    error_msg = f"Ricci scalar mismatch: claimed {claimed_R}, computed {actual_R}"

            elif rule == "riemann_curvature":
                return self._not_applicable(
                    rule,
                    "Riemann tensor claims are not compared by TensorChecker yet.",
                    {},
                    start_time,
                )

            elif rule == "ricci_curvature":
                actual_ricci = tg.ricci_tensor()
                component = params.get("component")
                if component is not None:
                    # Specific component check e.g. [0, 0] or (0, 0)
                    i, j = component[0], component[1]
                    parser = SafeParser(extra_symbols={str(s): s for s in coord_syms})
                    claimed_val = parser.parse(claim_str)
                    diff = sp.simplify(actual_ricci[i, j] - claimed_val)
                    passed = (diff == 0)
                    details = {
                        "rule": rule,
                        "component": f"R_{{{i}{j}}}",
                        "actual": str(actual_ricci[i, j]),
                        "claimed": str(claimed_val),
                        "diff": str(diff)
                    }
                    if not passed:
                        error_msg = f"Ricci tensor component R_{{{i}{j}}} mismatch: diff={diff}"
                else:
                    # Whole tensor check (e.g. claim "0" for Ricci-flat vacuum)
                    if claim_str in ("0", "zeros", "zero"):
                        n = len(coord_syms)
                        all_zero = True
                        for i in range(n):
                            for j in range(n):
                                if sp.simplify(actual_ricci[i, j]) != 0:
                                    all_zero = False
                                    break
                        passed = all_zero
                        details = {"rule": rule, "claimed_vacuum": True, "ricci_flat": passed}
                        if not passed:
                            error_msg = "Metric is not Ricci-flat; non-zero Ricci tensor components detected."
                    else:
                        return self._not_applicable(
                            rule,
                            "Whole-tensor Ricci claims are not compared yet. "
                            "Provide a component parameter or claim Ricci flatness with '0'.",
                            {"actual_ricci_tensor": str(actual_ricci)},
                            start_time,
                        )

            elif rule == "einstein_tensor":
                actual_einstein = tg.einstein_tensor()
                component = params.get("component")
                if component is not None:
                    i, j = component[0], component[1]
                    parser = SafeParser(extra_symbols={str(s): s for s in coord_syms})
                    claimed_val = parser.parse(claim_str)
                    diff = sp.simplify(actual_einstein[i, j] - claimed_val)
                    passed = (diff == 0)
                    details = {
                        "rule": rule,
                        "component": f"G_{{{i}{j}}}",
                        "actual": str(actual_einstein[i, j]),
                        "claimed": str(claimed_val),
                        "diff": str(diff)
                    }
                    if not passed:
                        error_msg = f"Einstein tensor component G_{{{i}{j}}} mismatch: diff={diff}"
                else:
                    if claim_str in ("0", "zeros", "zero"):
                        n = len(coord_syms)
                        all_zero = True
                        for i in range(n):
                            for j in range(n):
                                if sp.simplify(actual_einstein[i, j]) != 0:
                                    all_zero = False
                                    break
                        passed = all_zero
                        details = {"rule": rule, "claimed_vacuum": True, "einstein_flat": passed}
                        if not passed:
                            error_msg = "Einstein tensor is non-zero in vacuum."
                    else:
                        return self._not_applicable(
                            rule,
                            "Whole-tensor Einstein claims are not compared yet. "
                            "Provide a component parameter or claim a zero tensor with '0'.",
                            {"actual_einstein_tensor": str(actual_einstein)},
                            start_time,
                        )

            elif rule == "christoffel_symbols":
                actual_gamma = tg.christoffel_symbols()
                component = params.get("component")
                if component is not None:
                    # component is tuple (sigma, mu, nu)
                    key = tuple(component)
                    actual_val = actual_gamma.get(key, sp.Integer(0))
                    parser = SafeParser(extra_symbols={str(s): s for s in coord_syms})
                    claimed_val = parser.parse(claim_str)
                    diff = sp.simplify(actual_val - claimed_val)
                    passed = (diff == 0)
                    details = {
                        "rule": rule,
                        "component": f"Γ^{key[0]}_{{{key[1]}{key[2]}}}",
                        "actual": str(actual_val),
                        "claimed": str(claimed_val),
                        "diff": str(diff)
                    }
                    if not passed:
                        error_msg = f"Christoffel symbol Γ^{key[0]}_{{{key[1]}{key[2]}}} mismatch: diff={diff}"
                else:
                    return self._not_applicable(
                        rule,
                        "Whole-array Christoffel claims are not compared yet. "
                        "Provide a component parameter.",
                        {
                            "non_zero_count": len([
                                value for value in actual_gamma.values() if value != 0
                            ]),
                        },
                        start_time,
                    )

            elif rule in ("index_contract", "raise_index", "lower_index"):
                return self._not_applicable(
                    rule,
                    "Typed tensor index operations are not connected to TensorChecker claims yet.",
                    {},
                    start_time,
                )

            elif rule == "geodesic_equations":
                eqs = tg.geodesic_equations()
                coord_idx = params.get("coordinate_index")
                return self._not_applicable(
                    rule,
                    "Computed geodesic equations are not compared with the proposed claim yet.",
                    {
                        "coordinate_index": coord_idx,
                        "computed_equations": [str(eq) for eq in eqs],
                    },
                    start_time,
                )

            # 6. Multi-Engine Cross-Validation with EinsteinPy
            if self._ep_available and passed:
                cross_rep = cross_check_geometry(
                    metric=metric_matrix,
                    coords=coord_syms,
                    native_christoffel=tg.christoffel_symbols() if rule == "christoffel_symbols" else None,
                    native_ricci=tg.ricci_tensor() if rule == "ricci_curvature" else None,
                    native_ricci_scalar=tg.ricci_scalar() if rule == "ricci_scalar" else None,
                    native_einstein=tg.einstein_tensor() if rule == "einstein_tensor" else None,
                )
                details["cross_check"] = cross_rep
                if cross_rep.get("all_matched"):
                    independence_class = "DIFFERENT_ENGINE"
                elif cross_rep.get("all_matched") is False:
                    # Discrepancy detected between Automate and EinsteinPy
                    independence_class = "DISCREPANCY_DETECTED"
                    passed = False
                    error_msg = f"Independent oracle discrepancy with EinsteinPy: {cross_rep.get('discrepancies')}"
            else:
                details["cross_check"] = {"available": False, "reason": "EinsteinPy cross-check not run or not applicable"}

        except SafeParseError as spe:
            passed = False
            error_msg = f"SafeParser rejected tensor expression: {spe}"
        except Exception as e:
            passed = False
            error_msg = f"Tensor computation failed: {type(e).__name__}: {str(e)}"

        elapsed = (time.perf_counter() - start_time) * 1000
        status = VerificationStatus.SYMBOLIC_CHECKED if passed else VerificationStatus.FAILED

        # Certificate and evidence
        cert = None
        if passed:
            edge.status = status
            edge.checker = "tensor"
            cert = DerivationCertificate(
                rule_name=rule,
                proof_code=f"TensorGeometry({metric_matrix}, {coord_syms})",
                backend_version=self.version,
                execution_time_ms=elapsed,
                metrics={"independence_class": independence_class},
                diagnostics=[f"Independence Class: {independence_class}"]
            )
            edge.certificate = cert

        details["independence_class"] = independence_class

        return VerificationReport(
            status=status,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=passed,
            details=details,
            error_message=error_msg,
            certificate=cert
        )

    def _not_applicable(
        self,
        rule: str,
        reason: str,
        details: Dict[str, Any],
        start_time: float,
    ) -> VerificationReport:
        elapsed = (time.perf_counter() - start_time) * 1000
        return VerificationReport(
            status=VerificationStatus.NOT_APPLICABLE,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=False,
            details={"rule": rule, **details},
            error_message=reason,
        )

    def _build_tensor_geometry(
        self, in_node: Any, params: Dict[str, Any]
    ) -> Tuple[TensorGeometry, sp.Matrix, List[sp.Symbol]]:
        """Constructs TensorGeometry from in_node and edge parameters."""
        raw_str = in_node.expression.raw_str.strip()
        named_metric = params.get("named_metric") or raw_str

        # Predefined canonical metrics
        if named_metric in ("schwarzschild_4d", "schwarzschild"):
            t, r, theta, phi = sp.symbols("t r theta phi", real=True)
            M = sp.Symbol("M", positive=True)
            f = 1 - 2 * M / r
            g = sp.Matrix([
                [-f, 0, 0, 0],
                [0, 1 / f, 0, 0],
                [0, 0, r**2, 0],
                [0, 0, 0, r**2 * sp.sin(theta)**2],
            ])
            coords = [t, r, theta, phi]
            tg = TensorGeometry(g, coords, simplify=False)
            return tg, g, coords

        elif named_metric in ("polar_2d", "polar"):
            r, theta = sp.symbols("r theta", positive=True)
            g = sp.Matrix([[1, 0], [0, r**2]])
            coords = [r, theta]
            tg = TensorGeometry(g, coords, simplify=True)
            return tg, g, coords

        elif named_metric in ("sphere_2d", "sphere"):
            theta, phi = sp.symbols("theta phi", real=True)
            r = sp.Symbol("r", positive=True)
            g = sp.Matrix([[r**2, 0], [0, r**2 * sp.sin(theta)**2]])
            coords = [theta, phi]
            tg = TensorGeometry(g, coords, simplify=True)
            return tg, g, coords

        elif named_metric in ("flat_2d", "euclidean_2d"):
            x, y = sp.symbols("x y", real=True)
            g = sp.Matrix([[1, 0], [0, 1]])
            coords = [x, y]
            tg = TensorGeometry(g, coords, simplify=True)
            return tg, g, coords

        elif named_metric in ("flat_4d", "minkowski_4d", "minkowski"):
            t, x, y, z = sp.symbols("t x y z", real=True)
            g = sp.Matrix([
                [-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ])
            coords = [t, x, y, z]
            tg = TensorGeometry(g, coords, simplify=True)
            return tg, g, coords

        # Custom metric provided via parameters
        coord_names = params.get("coordinates", ["x", "y"])
        coords = [sp.Symbol(name, real=True) for name in coord_names]
        metric_spec = params.get("metric")

        if isinstance(metric_spec, list):
            # List of lists representing matrix rows
            parser = SafeParser(extra_symbols={str(s): s for s in coords})
            matrix_rows = []
            for row in metric_spec:
                parsed_row = [parser.parse(str(val)) if isinstance(val, (str, int, float)) else val for val in row]
                matrix_rows.append(parsed_row)
            g = sp.Matrix(matrix_rows)
            tg = TensorGeometry(g, coords, simplify=params.get("simplify", True))
            return tg, g, coords

        # Fallback: diagonal metric from list
        diag_spec = params.get("diag")
        if diag_spec and isinstance(diag_spec, list):
            parser = SafeParser(extra_symbols={str(s): s for s in coords})
            diag_vals = [parser.parse(str(val)) for val in diag_spec]
            g = sp.diag(*diag_vals)
            tg = TensorGeometry(g, coords, simplify=params.get("simplify", True))
            return tg, g, coords

        raise ValueError(f"Unable to parse metric specification from node '{raw_str}' or parameters.")
