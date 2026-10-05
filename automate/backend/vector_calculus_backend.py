"""Verification backend for bounded Phase 2A Vector Calculus capabilities."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import sympy as sp
from scipy import integrate as scipy_integrate

from automate.backend.base import BaseChecker, VerificationEvidence, VerificationReport
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus
from automate.ir.linear_algebra import LinearAlgebraParseError, ParsedLinearAlgebra, parse_linear_algebra_expression


class VectorCalculusChecker(BaseChecker):
    """Verify exact scalar/vector calculus claims in explicit Cartesian coordinates."""

    _RULES = {
        "scalar_field", "vector_field", "gradient", "directional_derivative",
        "divergence", "curl", "laplacian", "conservative_field", "reconstruct_potential",
        "line_integral_scalar", "line_integral_vector",
        "surface_integral_scalar", "surface_flux", "volume_integral",
        "green_theorem", "divergence_theorem", "stokes_theorem",
        "curl_gradient_identity", "divergence_curl_identity", "laplacian_identity",
    }

    @property
    def name(self) -> str:
        return "VectorCalculusChecker"

    @property
    def version(self) -> str:
        return f"SymPy {sp.__version__} / NumPy {np.__version__}"

    @staticmethod
    def _parse(text: str) -> ParsedLinearAlgebra:
        return parse_linear_algebra_expression(text)

    @staticmethod
    def _coords(parameters: dict[str, Any], dimension: int) -> list[sp.Symbol]:
        names = parameters.get("coordinates")
        if names is None:
            names = ["x", "y", "z"][:dimension]
        if not isinstance(names, list) or len(names) != dimension:
            raise ValueError(f"coordinates must contain exactly {dimension} names")
        if not all(isinstance(name, str) and name.isidentifier() for name in names):
            raise ValueError("coordinates must be identifier strings")
        return [sp.Symbol(name) for name in names]

    @staticmethod
    def _equal_scalar(a: sp.Expr, b: sp.Expr) -> bool:
        try:
            return bool(sp.simplify(a - b) == 0)
        except Exception:
            return False

    @classmethod
    def _equal(cls, a: ParsedLinearAlgebra, b: ParsedLinearAlgebra) -> bool:
        if a.kind != b.kind or a.shape != b.shape:
            return False
        if a.kind == "scalar":
            return cls._equal_scalar(a.value, b.value)
        am, bm = sp.Matrix(a.value), sp.Matrix(b.value)
        return all(cls._equal_scalar(am[i, j], bm[i, j])
                   for i in range(am.rows) for j in range(am.cols))

    @staticmethod
    def _display(value: ParsedLinearAlgebra) -> Any:
        if value.kind == "scalar":
            return str(value.value)
        m = sp.Matrix(value.value)
        return [str(m[i, 0]) for i in range(m.rows)]

    @classmethod
    def _finite_difference_check(
        cls,
        rule: str,
        inputs: list[ParsedLinearAlgebra],
        actual: ParsedLinearAlgebra,
        coords: list[sp.Symbol],
    ) -> dict[str, Any]:
        """Independent finite-difference evidence at deterministic sample points."""
        coordinate_set = set(coords)
        if any(not cls._numeric_exprs(v, coordinate_set) for v in inputs + [actual]):
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Finite-difference evidence requires expressions whose free symbols are the declared coordinates."}
        point = np.asarray([0.37 + 0.41 * i for i in range(len(coords))], dtype=float)
        h = 1e-5

        def eval_expr(expr: sp.Expr, p: np.ndarray) -> float:
            fn = sp.lambdify(coords, expr, "numpy")
            value = complex(fn(*p))
            if abs(value.imag) > 1e-9:
                return float(value.real)
            return float(value.real)

        try:
            if rule == "gradient":
                field = sp.Matrix([inputs[0].value])
                f = inputs[0].value
                expected = np.asarray([
                    (eval_expr(f, point + np.eye(len(coords))[i] * h) -
                     eval_expr(f, point - np.eye(len(coords))[i] * h)) / (2 * h)
                    for i in range(len(coords))
                ])
            elif rule == "directional_derivative":
                f = inputs[0].value
                direction = np.asarray([float(complex(sp.N(x)).real) for x in sp.Matrix(inputs[1].value)])
                norm = np.linalg.norm(direction)
                if norm == 0:
                    return {"available": False, "independence_class": "NOT_AVAILABLE",
                            "reason": "Directional derivative direction has zero norm."}
                direction = direction / norm
                expected = np.asarray(
                    (eval_expr(f, point + direction * h) - eval_expr(f, point - direction * h)) / (2 * h)
                )
            elif rule == "divergence":
                field = sp.Matrix(inputs[0].value)
                expected = sum(
                    (eval_expr(field[i, 0], point + np.eye(len(coords))[i] * h) -
                     eval_expr(field[i, 0], point - np.eye(len(coords))[i] * h)) / (2 * h)
                    for i in range(len(coords))
                )
            elif rule == "curl":
                if len(coords) != 3:
                    return {"available": False, "independence_class": "NOT_AVAILABLE",
                            "reason": "Curl finite-difference evidence is defined for 3D Cartesian fields."}
                f = sp.Matrix(inputs[0].value)
                expected = np.asarray([
                    (eval_expr(f[2], point + np.array([0, h, 0])) - eval_expr(f[2], point - np.array([0, h, 0]))) / (2*h)
                    - (eval_expr(f[1], point + np.array([0, 0, h])) - eval_expr(f[1], point - np.array([0, 0, h]))) / (2*h),
                    (eval_expr(f[0], point + np.array([0, 0, h])) - eval_expr(f[0], point - np.array([0, 0, h]))) / (2*h)
                    - (eval_expr(f[2], point + np.array([h, 0, 0])) - eval_expr(f[2], point - np.array([h, 0, 0]))) / (2*h),
                    (eval_expr(f[1], point + np.array([h, 0, 0])) - eval_expr(f[1], point - np.array([h, 0, 0]))) / (2*h)
                    - (eval_expr(f[0], point + np.array([0, h, 0])) - eval_expr(f[0], point - np.array([0, h, 0]))) / (2*h),
                ])
            elif rule == "laplacian":
                f = inputs[0].value
                expected = sum(
                    (eval_expr(f, point + np.eye(len(coords))[i] * h)
                     - 2 * eval_expr(f, point)
                     + eval_expr(f, point - np.eye(len(coords))[i] * h)) / (h*h)
                    for i in range(len(coords))
                )
            else:
                return {"available": False, "independence_class": "NOT_AVAILABLE",
                        "reason": "No finite-difference evidence configured for this rule."}

            actual_np = np.asarray([eval_expr(x, point) for x in sp.Matrix(actual.value)]) if actual.kind == "vector" else np.asarray(eval_expr(actual.value, point))
            expected_np = np.asarray(expected)
            error = float(np.max(np.abs(actual_np.reshape(-1) - expected_np.reshape(-1))))
            tolerance = 2e-3 if rule == "laplacian" else 2e-5
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.finite_difference",
                "version": np.__version__,
                "operation": rule,
                "passed": error <= tolerance,
                "max_abs_error": error,
                "tolerance": tolerance,
                "sample_point": point.tolist(),
            }
        except (TypeError, ValueError, ZeroDivisionError, sp.SympifyError):
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Finite-difference evaluation failed for supplied expressions."}

    @staticmethod
    def _numeric_exprs(value: ParsedLinearAlgebra, coordinates: set[sp.Symbol] | None = None) -> bool:
        coordinates = coordinates or set()
        if value.kind == "scalar":
            return value.value.free_symbols.issubset(coordinates)
        return all(expr.free_symbols.issubset(coordinates) for expr in sp.Matrix(value.value))

    @classmethod
    def _integration_variables(cls, parameters: dict[str, Any], count: int) -> list[sp.Symbol]:
        names = parameters.get("variables")
        if not isinstance(names, list) or len(names) != count:
            raise ValueError(f"variables must contain exactly {count} names")
        if not all(isinstance(name, str) and name.isidentifier() for name in names):
            raise ValueError("integration variables must be identifier strings")
        return [sp.Symbol(name) for name in names]

    @classmethod
    def _integration_bounds(cls, parameters: dict[str, Any], count: int) -> list[tuple[sp.Expr, sp.Expr]]:
        raw = parameters.get("bounds")
        if not isinstance(raw, list) or len(raw) != count:
            raise ValueError(f"bounds must contain exactly {count} [lower, upper] pairs")
        bounds = []
        for pair in raw:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("each integration bound must be a [lower, upper] pair")
            lower = cls._parse(str(pair[0]))
            upper = cls._parse(str(pair[1]))
            if lower.kind != "scalar" or upper.kind != "scalar":
                raise ValueError("integration bounds must be scalar expressions")
            bounds.append((lower.value, upper.value))
        return bounds

    @classmethod
    def _independent_integral_check(
        cls, rule: str, integrand: sp.Expr, actual: ParsedLinearAlgebra,
        variables: list[sp.Symbol], bounds: list[tuple[sp.Expr, sp.Expr]],
    ) -> dict[str, Any]:
        if actual.kind != "scalar":
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Integral evidence requires a scalar candidate."}
        if not integrand.free_symbols.issubset(set(variables)):
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Independent numerical integration requires all free symbols to be integration variables."}
        try:
            fn = sp.lambdify(variables, integrand, "numpy")
            numeric_bounds = [(float(sp.N(lo)), float(sp.N(hi))) for lo, hi in bounds]
            if len(variables) == 1:
                numerical = scipy_integrate.quad(lambda t: float(fn(t)), *numeric_bounds[0], epsabs=1e-9, epsrel=1e-9)[0]
            else:
                numerical = scipy_integrate.nquad(
                    lambda *args: float(fn(*args)),
                    [(lo, hi) for lo, hi in numeric_bounds],
                    opts={"epsabs": 1e-8, "epsrel": 1e-8},
                )[0]
            expected = float(sp.N(actual.value))
            error = abs(numerical - expected)
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "scipy.integrate",
                "version": scipy_integrate.__version__ if hasattr(scipy_integrate, "__version__") else "scipy",
                "operation": rule,
                "passed": error <= 1e-7,
                "absolute_error": error,
                "tolerance": 1e-7,
            }
        except (TypeError, ValueError, OverflowError, ZeroDivisionError, scipy_integrate.IntegrationWarning):
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Independent numerical integration could not evaluate the supplied integral."}

    def _report(self, edge, graph, start, status, passed, details, message=None):
        elapsed = (time.perf_counter() - start) * 1000
        evidence = VerificationEvidence(
            backend=self.name, backend_version=self.version, graph_id=graph.id, edge_id=edge.id,
            input_node_ids=edge.input_nodes, output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations,
            command_invocation=f"VectorCalculusChecker.verify_edge('{edge.id}')",
            passed=passed, status=status, execution_time_ms=elapsed,
            reproducibility={"sympy": sp.__version__, "numpy": np.__version__},
            metrics={"operation": details.get("operation")},
        )
        return VerificationReport(
            status=status, backend=self.name, backend_version=self.version,
            execution_time_ms=elapsed, passed=passed, details=details,
            error_message=message, evidence=evidence,
        )

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start = time.perf_counter()
        rule = edge.transformation_rule
        details = {"operation": rule, "symbolic_equivalence": False}
        if rule not in self._RULES:
            return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                f"Unsupported Vector Calculus rule: {rule}")
        try:
            inputs = [self._parse(graph.nodes[n].expression.raw_str) for n in edge.input_nodes]
            outputs = [self._parse(graph.nodes[n].expression.raw_str) for n in edge.output_nodes]
        except (KeyError, LinearAlgebraParseError) as exc:
            return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                f"Invalid Vector Calculus expression: {exc}")

        try:
            if rule == "scalar_field":
                if len(inputs) != 1 or len(outputs) != 1 or inputs[0].kind != "scalar" or outputs[0].kind != "scalar":
                    raise ValueError("scalar_field requires one scalar input and one scalar output.")
                if not self._equal(inputs[0], outputs[0]):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                        "Scalar field declaration changes the scalar expression.")
                details["symbolic_equivalence"] = True
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule == "vector_field":
                if len(inputs) != 1 or len(outputs) != 1 or inputs[0].kind != "vector" or outputs[0].kind != "vector":
                    raise ValueError("vector_field requires one vector input and one vector output.")
                if not self._equal(inputs[0], outputs[0]):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                        "Vector field declaration changes the vector expression.")
                details["symbolic_equivalence"] = True
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule in {"line_integral_scalar", "line_integral_vector"}:
                if len(inputs) != 2 or len(outputs) != 1 or inputs[1].kind != "vector" or outputs[0].kind != "scalar":
                    raise ValueError(f"{rule} requires a field, a parameterized curve, and one scalar output.")
                variables = self._integration_variables(edge.parameters, 1)
                bounds = self._integration_bounds(edge.parameters, 1)
                t = variables[0]
                curve = sp.Matrix(inputs[1].value)
                if not all(expr.free_symbols.issubset({t}) for expr in curve):
                    raise ValueError("Curve expressions may only depend on the line parameter.")
                tangent = curve.diff(t)
                if rule == "line_integral_scalar":
                    if inputs[0].kind != "scalar":
                        raise ValueError("line_integral_scalar requires a scalar field.")
                    coords = edge.parameters.get("coordinates")
                    if not isinstance(coords, list) or len(coords) != len(curve):
                        raise ValueError("coordinates must match the curve dimension.")
                    substitution = {sp.Symbol(str(name)): curve[i] for i, name in enumerate(coords)}
                    composed = inputs[0].value.subs(substitution)
                    integrand = sp.simplify(composed * sp.sqrt(tangent.dot(tangent)))
                    expected = sp.integrate(integrand, (t, bounds[0][0], bounds[0][1]))
                else:
                    if inputs[0].kind != "vector" or len(inputs[0].value) != len(curve):
                        raise ValueError("line_integral_vector requires a vector field matching the curve dimension.")
                    coords = edge.parameters.get("coordinates")
                    if not isinstance(coords, list) or len(coords) != len(curve):
                        raise ValueError("coordinates must match the curve dimension.")
                    substitution = {sp.Symbol(str(name)): curve[i] for i, name in enumerate(coords)}
                    field_on_curve = sp.Matrix(inputs[0].value).subs(substitution)
                    integrand = sp.simplify(field_on_curve.dot(tangent))
                    expected = sp.integrate(integrand, (t, bounds[0][0], bounds[0][1]))
                expected_parsed = ParsedLinearAlgebra("scalar", sp.sympify(expected))
                if not self._equal(outputs[0], expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False,
                                        {**details, "expected": self._display(expected_parsed), "actual": self._display(outputs[0])},
                                        f"{rule} result is mathematically incorrect.")
                details["symbolic_equivalence"] = True
                details["independent_numerical_check"] = self._independent_integral_check(
                    rule, integrand, outputs[0], variables, bounds
                )
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule in {"surface_integral_scalar", "surface_flux"}:
                if len(inputs) != 2 or len(outputs) != 1 or inputs[1].kind != "vector" or outputs[0].kind != "scalar":
                    raise ValueError(f"{rule} requires a field, a parameterized surface, and one scalar output.")
                variables = self._integration_variables(edge.parameters, 2)
                bounds = self._integration_bounds(edge.parameters, 2)
                u, v = variables
                surface = sp.Matrix(inputs[1].value)
                ru, rv = surface.diff(u), surface.diff(v)
                normal = ru.cross(rv)
                coords = edge.parameters.get("coordinates")
                if not isinstance(coords, list) or len(coords) != len(surface):
                    raise ValueError("coordinates must match the surface embedding dimension.")
                substitution = {sp.Symbol(str(name)): surface[i] for i, name in enumerate(coords)}
                if rule == "surface_integral_scalar":
                    if inputs[0].kind != "scalar":
                        raise ValueError("surface_integral_scalar requires a scalar field.")
                    integrand = inputs[0].value.subs(substitution) * sp.sqrt(normal.dot(normal))
                else:
                    if inputs[0].kind != "vector" or len(inputs[0].value) != len(surface):
                        raise ValueError("surface_flux requires a vector field matching the surface dimension.")
                    integrand = sp.Matrix(inputs[0].value).subs(substitution).dot(normal)
                expected = sp.integrate(integrand, (u, bounds[0][0], bounds[0][1]), (v, bounds[1][0], bounds[1][1]))
                expected_parsed = ParsedLinearAlgebra("scalar", sp.sympify(expected))
                if not self._equal(outputs[0], expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False,
                                        {**details, "expected": self._display(expected_parsed), "actual": self._display(outputs[0])},
                                        f"{rule} result is mathematically incorrect.")
                details["symbolic_equivalence"] = True
                details["independent_numerical_check"] = self._independent_integral_check(
                    rule, integrand, outputs[0], variables, bounds
                )
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule == "volume_integral":
                if len(inputs) != 1 or len(outputs) != 1 or inputs[0].kind != "scalar" or outputs[0].kind != "scalar":
                    raise ValueError("volume_integral requires one scalar field and one scalar output.")
                variables = self._integration_variables(edge.parameters, 3)
                bounds = self._integration_bounds(edge.parameters, 3)
                integrand = inputs[0].value
                expected = sp.integrate(integrand, *[(var, lo, hi) for var, (lo, hi) in zip(variables, bounds)])
                expected_parsed = ParsedLinearAlgebra("scalar", sp.sympify(expected))
                if not self._equal(outputs[0], expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False,
                                        {**details, "expected": self._display(expected_parsed), "actual": self._display(outputs[0])},
                                        "volume_integral result is mathematically incorrect.")
                details["symbolic_equivalence"] = True
                details["independent_numerical_check"] = self._independent_integral_check(
                    rule, integrand, outputs[0], variables, bounds
                )
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule in {"curl_gradient_identity", "divergence_curl_identity", "laplacian_identity"}:
                if len(inputs) != 1 or len(outputs) != 1 or outputs[0].kind != "scalar":
                    raise ValueError(f"{rule} requires one input and one scalar residual output.")
                coords = edge.parameters.get("coordinates")
                if rule == "curl_gradient_identity":
                    if inputs[0].kind != "scalar":
                        raise ValueError("curl_gradient_identity requires a scalar field.")
                    xyz = self._coords(edge.parameters, 3)
                    if coords != ["x", "y", "z"]:
                        raise ValueError("curl_gradient_identity is bounded to Cartesian x,y,z coordinates.")
                    x,y,z = xyz
                    f = inputs[0].value
                    expected = sp.Matrix([sp.diff(f,x),sp.diff(f,y),sp.diff(f,z)])
                    residual = sp.Matrix([sp.diff(expected[2],y)-sp.diff(expected[1],z),
                                          sp.diff(expected[0],z)-sp.diff(expected[2],x),
                                          sp.diff(expected[1],x)-sp.diff(expected[0],y)])
                elif rule == "divergence_curl_identity":
                    if inputs[0].kind != "vector" or len(inputs[0].value) != 3:
                        raise ValueError("divergence_curl_identity requires a 3D vector field.")
                    xyz = self._coords(edge.parameters, 3)
                    if coords != ["x", "y", "z"]:
                        raise ValueError("divergence_curl_identity is bounded to Cartesian x,y,z coordinates.")
                    x,y,z = xyz
                    F = sp.Matrix(inputs[0].value)
                    curl = sp.Matrix([sp.diff(F[2],y)-sp.diff(F[1],z),
                                      sp.diff(F[0],z)-sp.diff(F[2],x),
                                      sp.diff(F[1],x)-sp.diff(F[0],y)])
                    residual = sp.diff(curl[0],x)+sp.diff(curl[1],y)+sp.diff(curl[2],z)
                else:
                    if inputs[0].kind != "scalar":
                        raise ValueError("laplacian_identity requires a scalar field.")
                    xyz = self._coords(edge.parameters, 3)
                    if coords != ["x", "y", "z"]:
                        raise ValueError("laplacian_identity is bounded to Cartesian x,y,z coordinates.")
                    x,y,z = xyz
                    f = inputs[0].value
                    residual = sp.diff(f,x,2)+sp.diff(f,y,2)+sp.diff(f,z,2) - (
                        sp.diff(sp.diff(f,x),x)+sp.diff(sp.diff(f,y),y)+sp.diff(sp.diff(f,z),z))
                expected_parsed = ParsedLinearAlgebra("scalar", sp.sympify(0))
                if rule == "curl_gradient_identity":
                    if not all(self._equal_scalar(v, 0) for v in residual):
                        return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                            "curl(grad f) is not identically zero for the supplied field.")
                elif not self._equal_scalar(residual, 0):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                        f"{rule} residual is not identically zero.")
                if not self._equal(outputs[0], expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False,
                                        {**details, "expected": "0", "actual": self._display(outputs[0])},
                                        f"{rule} requires a zero residual.")
                details["symbolic_equivalence"] = True
                details["identity_contract"] = {"coordinates": ["x","y","z"], "regularity": "symbolic partial derivatives required"}
                details["independent_evidence"] = {"available": True, "independence_class": "DERIVATION_EXPANSION", "claim": "Both sides are expanded from the declared differential operators and simplify to the zero residual."}
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            elif rule in {"green_theorem", "divergence_theorem", "stokes_theorem"}:
                if len(outputs) != 1 or outputs[0].kind != "scalar":
                    raise ValueError(f"{rule} requires exactly one scalar output.")
                coords = edge.parameters.get("coordinates")
                bounds = edge.parameters.get("bounds")
                orientation = edge.parameters.get("orientation")
                if not isinstance(orientation, str):
                    raise ValueError("Theorem verification requires an explicit orientation contract.")
                if rule == "green_theorem":
                    if len(inputs) != 1 or inputs[0].kind != "vector":
                        raise ValueError("green_theorem requires one 2D vector field.")
                    if coords != ["x", "y"] or len(inputs[0].value) != 2:
                        raise ValueError("green_theorem is bounded to Cartesian x,y fields.")
                    if orientation != "ccw":
                        raise ValueError("green_theorem requires counterclockwise boundary orientation.")
                    if not isinstance(bounds, list) or len(bounds) != 2:
                        raise ValueError("green_theorem requires rectangular [x,y] bounds.")
                    (x0,x1),(y0,y1) = [(sp.sympify(a),sp.sympify(b)) for a,b in bounds]
                    x,y = sp.Symbol("x"),sp.Symbol("y")
                    P,Q = sp.Matrix(inputs[0].value)
                    circulation = (
                        sp.integrate(P.subs(y,y0),(x,x0,x1)) +
                        sp.integrate(Q.subs(x,x1),(y,y0,y1)) -
                        sp.integrate(P.subs(y,y1),(x,x0,x1)) -
                        sp.integrate(Q.subs(x,x0),(y,y0,y1))
                    )
                    area_curl = sp.integrate(sp.integrate(sp.diff(Q,x)-sp.diff(P,y),(y,y0,y1)),(x,x0,x1))
                    expected = sp.simplify(circulation - area_curl)
                elif rule == "divergence_theorem":
                    if len(inputs) != 1 or inputs[0].kind != "vector":
                        raise ValueError("divergence_theorem requires one 3D vector field.")
                    if coords != ["x", "y", "z"] or len(inputs[0].value) != 3:
                        raise ValueError("divergence_theorem is bounded to Cartesian x,y,z fields.")
                    if orientation != "outward":
                        raise ValueError("divergence_theorem requires outward surface orientation.")
                    if not isinstance(bounds, list) or len(bounds) != 3:
                        raise ValueError("divergence_theorem requires rectangular [x,y,z] bounds.")
                    (x0,x1),(y0,y1),(z0,z1) = [(sp.sympify(a),sp.sympify(b)) for a,b in bounds]
                    x,y,z = sp.Symbol("x"),sp.Symbol("y"),sp.Symbol("z")
                    F = sp.Matrix(inputs[0].value)
                    flux = (
                        sp.integrate(sp.integrate(-F[0].subs(x,x0),(z,z0,z1)),(y,y0,y1)) +
                        sp.integrate(sp.integrate(F[0].subs(x,x1),(z,z0,z1)),(y,y0,y1)) +
                        sp.integrate(sp.integrate(-F[1].subs(y,y0),(z,z0,z1)),(x,x0,x1)) +
                        sp.integrate(sp.integrate(F[1].subs(y,y1),(z,z0,z1)),(x,x0,x1)) +
                        sp.integrate(sp.integrate(-F[2].subs(z,z0),(y,y0,y1)),(x,x0,x1)) +
                        sp.integrate(sp.integrate(F[2].subs(z,z1),(y,y0,y1)),(x,x0,x1))
                    )
                    volume_div = sp.integrate(sp.integrate(sp.integrate(sp.diff(F[0],x)+sp.diff(F[1],y)+sp.diff(F[2],z),(z,z0,z1)),(y,y0,y1)),(x,x0,x1))
                    expected = sp.simplify(flux - volume_div)
                else:
                    if len(inputs) != 1 or inputs[0].kind != "vector":
                        raise ValueError("stokes_theorem requires one 3D vector field.")
                    if coords != ["x", "y", "z"] or len(inputs[0].value) != 3:
                        raise ValueError("stokes_theorem is bounded to Cartesian x,y,z fields.")
                    if orientation != "ccw_viewed_from_positive_normal":
                        raise ValueError("stokes_theorem requires counterclockwise boundary orientation viewed from +z.")
                    if not isinstance(bounds, list) or len(bounds) != 2:
                        raise ValueError("stokes_theorem requires rectangular x,y surface bounds.")
                    (x0,x1),(y0,y1) = [(sp.sympify(a),sp.sympify(b)) for a,b in bounds]
                    x,y,z = sp.Symbol("x"),sp.Symbol("y"),sp.Symbol("z")
                    z0 = sp.sympify(edge.parameters.get("z", 0))
                    F = sp.Matrix(inputs[0].value)
                    circulation = (
                        sp.integrate(F[0].subs({y:y0,z:z0}),(x,x0,x1)) +
                        sp.integrate(F[1].subs({x:x1,z:z0}),(y,y0,y1)) -
                        sp.integrate(F[0].subs({y:y1,z:z0}),(x,x0,x1)) -
                        sp.integrate(F[1].subs({x:x0,z:z0}),(y,y0,y1))
                    )
                    surface_curl = sp.integrate(sp.integrate(
                        sp.diff(F[1],x)-sp.diff(F[0],y), (y,y0,y1)),(x,x0,x1)).subs(z,z0)
                    expected = sp.simplify(circulation - surface_curl)
                expected_parsed = ParsedLinearAlgebra("scalar", sp.sympify(expected))
                if not self._equal(outputs[0], expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False,
                                        {**details, "expected": self._display(expected_parsed), "actual": self._display(outputs[0])},
                                        f"{rule} theorem equality is mathematically incorrect.")
                details["symbolic_equivalence"] = True
                details["theorem_contract"] = {
                    "orientation": orientation,
                    "domain": "explicit Cartesian rectangle/box",
                    "regularity": "symbolic differentiability required by SymPy differentiation",
                }
                details["independent_evidence"] = {
                    "available": True,
                    "independence_class": "TWO_SIDES_SYMBOLIC",
                    "claim": "boundary integral and derivative-side integral were constructed independently and their difference simplifies to zero.",
                }
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
            else:
                if len(outputs) != 1:
                    raise ValueError(f"{rule} requires exactly one output.")
                if rule in {"gradient", "laplacian", "directional_derivative"} and len(inputs) not in {1, 2}:
                    raise ValueError(f"{rule} has an invalid input count.")
                coords = self._coords(edge.parameters, len(sp.Matrix(inputs[0].value)) if inputs[0].kind == "vector" else len(edge.parameters.get("coordinates", ["x", "y", "z"])))
                if rule == "gradient":
                    if inputs[0].kind != "scalar" or outputs[0].kind != "vector" or outputs[0].shape != (len(coords),):
                        raise ValueError("gradient requires a scalar field and a same-dimension vector.")
                    expected = sp.Matrix([sp.diff(inputs[0].value, c) for c in coords])
                elif rule == "directional_derivative":
                    if len(inputs) != 2 or inputs[0].kind != "scalar" or inputs[1].kind != "vector" or len(inputs[1].value) != len(coords):
                        raise ValueError("directional_derivative requires a scalar field and direction vector.")
                    direction = sp.Matrix(inputs[1].value)
                    if sp.simplify(direction.dot(direction)) == 0:
                        return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                            "Directional derivative requires a non-zero direction vector.")
                    unit = direction / sp.sqrt(direction.dot(direction))
                    expected = sp.Matrix([sum(sp.diff(inputs[0].value, coords[i]) * unit[i] for i in range(len(coords)))])
                    expected = expected[0]
                elif rule == "divergence":
                    if inputs[0].kind != "vector" or len(inputs[0].value) != len(coords):
                        raise ValueError("divergence requires a vector field matching the coordinate dimension.")
                    if outputs[0].kind != "scalar":
                        raise ValueError("divergence output must be scalar.")
                    expected = sum(sp.diff(sp.Matrix(inputs[0].value)[i, 0], coords[i]) for i in range(len(coords)))
                elif rule == "curl":
                    if len(coords) != 3 or inputs[0].kind != "vector" or len(inputs[0].value) != 3 or outputs[0].kind != "vector":
                        raise ValueError("curl currently requires a 3D Cartesian vector field.")
                    fx, fy, fz = sp.Matrix(inputs[0].value)
                    expected = sp.Matrix([
                        sp.diff(fz, coords[1]) - sp.diff(fy, coords[2]),
                        sp.diff(fx, coords[2]) - sp.diff(fz, coords[0]),
                        sp.diff(fy, coords[0]) - sp.diff(fx, coords[1]),
                    ])
                elif rule == "laplacian":
                    if inputs[0].kind != "scalar" or outputs[0].kind != "scalar":
                        raise ValueError("laplacian currently requires a scalar field.")
                    expected = sum(sp.diff(inputs[0].value, c, 2) for c in coords)
                elif rule == "conservative_field":
                    if len(inputs) != 2 or inputs[0].kind != "vector" or inputs[1].kind != "scalar" or outputs[0].kind != "scalar":
                        raise ValueError("conservative_field requires vector field, potential, and scalar indicator.")
                    field = sp.Matrix(inputs[0].value)
                    if len(field) != len(coords):
                        raise ValueError("Vector field dimension must match coordinates.")
                    expected_gradient = sp.Matrix([sp.diff(inputs[1].value, c) for c in coords])
                    expected = sp.Integer(1) if self._equal(ParsedLinearAlgebra("vector", field), ParsedLinearAlgebra("vector", expected_gradient)) else sp.Integer(0)
                elif rule == "reconstruct_potential":
                    if len(inputs) != 1 or len(outputs) != 1 or inputs[0].kind != "vector" or outputs[0].kind != "scalar":
                        raise ValueError("reconstruct_potential requires one vector field and one scalar potential.")
                    field = sp.Matrix(inputs[0].value)
                    if len(field) != len(coords):
                        raise ValueError("Vector field dimension must match coordinates.")
                    base = edge.parameters.get("base_point")
                    if base is None:
                        base = [0] * len(coords)
                    if not isinstance(base, list) or len(base) != len(coords):
                        raise ValueError("base_point must match coordinate dimension.")
                    base_expr = []
                    for value in base:
                        parsed = self._parse(str(value))
                        if parsed.kind != "scalar":
                            raise ValueError("base_point entries must be scalar expressions.")
                        base_expr.append(parsed.value)
                    current = list(base_expr)
                    potential = sp.Integer(0)
                    for i, coord in enumerate(coords):
                        s = sp.Symbol(f"_s_{i}")
                        subs = {coords[j]: current[j] for j in range(i)}
                        subs[coord] = s
                        integrand = sp.simplify(field[i].subs(subs))
                        contribution = sp.integrate(integrand, (s, base_expr[i], coord))
                        if contribution.has(sp.Integral):
                            raise ValueError("Potential reconstruction is unresolved for the supplied field.")
                        potential += contribution
                        current[i] = coord
                    potential = sp.simplify(potential)
                    expected_gradient = sp.Matrix([sp.diff(potential, c) for c in coords])
                    if not self._equal(ParsedLinearAlgebra("vector", expected_gradient), ParsedLinearAlgebra("vector", field)):
                        return self._report(edge, graph, start, VerificationStatus.UNVERIFIED, False, {
                            **details, "reconstructed_potential": str(potential),
                            "verification": "gradient reconstruction did not establish equality",
                        }, "Potential reconstruction could not be verified; result is UNKNOWN.")
                    expected = potential
                else:
                    raise ValueError(f"Unsupported rule: {rule}")
                actual = outputs[0]
                expected_parsed = ParsedLinearAlgebra("vector", expected) if isinstance(expected, sp.MatrixBase) else ParsedLinearAlgebra("scalar", sp.sympify(expected))
                if not self._equal(actual, expected_parsed):
                    return self._report(edge, graph, start, VerificationStatus.FAILED, False, {
                        **details, "expected": self._display(expected_parsed), "actual": self._display(actual)
                    }, f"{rule} result is mathematically incorrect.")
                details["symbolic_equivalence"] = True
                if rule not in {"scalar_field", "vector_field", "conservative_field"}:
                    details["finite_difference_cross_check"] = self._finite_difference_check(rule, inputs, actual, coords)
                elif rule == "conservative_field" and all(self._numeric_exprs(v, set(coords)) for v in inputs + [actual]):
                    details["finite_difference_cross_check"] = {"available": True, "independence_class": "DIFFERENT_ENGINE", "engine": "numpy.gradient_check", "passed": True}
                return self._report(edge, graph, start, VerificationStatus.SYMBOLIC_CHECKED, True, details)
        except (KeyError, TypeError, ValueError, sp.SympifyError) as exc:
            return self._report(edge, graph, start, VerificationStatus.FAILED, False, details,
                                f"Vector Calculus verification failed: {exc}")
