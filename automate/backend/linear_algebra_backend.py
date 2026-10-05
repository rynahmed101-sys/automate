"""Verification backend for the Phase 1A Linear Algebra Core."""

from __future__ import annotations

import keyword
import time
from typing import Any

import numpy as np
import sympy as sp

from automate.backend.base import BaseChecker, VerificationEvidence, VerificationReport
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus
from automate.ir.linear_algebra import (
    LinearAlgebraParseError,
    ParsedLinearAlgebra,
    parse_linear_algebra_expression,
)


class LinearAlgebraChecker(BaseChecker):
    """Verify explicit vector/matrix claims with exact symbolic semantics."""

    _RULES = {
        "vector_add", "vector_subtract", "vector_scalar_multiply", "vector_dot",
        "matrix_multiply", "matrix_transpose", "matrix_determinant", "matrix_trace",
        "matrix_inverse", "matrix_rank", "matrix_rref", "linear_system_solve",
        "matrix_characteristic_polynomial", "matrix_eigenvalues",
        "matrix_eigenvector", "matrix_diagonalize",
        "vector_inner_product", "vector_norm", "vector_orthogonal",
        "vector_projection", "vector_gram_schmidt",
    }

    @property
    def name(self) -> str:
        return "LinearAlgebraChecker"

    @property
    def version(self) -> str:
        return f"SymPy {sp.__version__} / NumPy {np.__version__}"

    @staticmethod
    def _display(value: ParsedLinearAlgebra) -> Any:
        if value.kind == "scalar":
            return str(value.value)
        matrix = sp.Matrix(value.value)
        if value.kind == "vector":
            return [str(matrix[i, 0]) for i in range(matrix.rows)]
        return [[str(matrix[i, j]) for j in range(matrix.cols)] for i in range(matrix.rows)]

    @staticmethod
    def _equal_scalar(actual: sp.Expr, expected: sp.Expr) -> bool:
        try:
            return bool(sp.simplify(actual - expected) == 0)
        except Exception:
            return False

    @classmethod
    def _equal(cls, actual: ParsedLinearAlgebra, expected: ParsedLinearAlgebra) -> bool:
        if actual.kind != expected.kind or actual.shape != expected.shape:
            return False
        if actual.kind == "scalar":
            return cls._equal_scalar(actual.value, expected.value)
        a, b = sp.Matrix(actual.value), sp.Matrix(expected.value)
        return all(cls._equal_scalar(a[i, j], b[i, j])
                   for i in range(a.rows) for j in range(a.cols))

    @classmethod
    def _symbolic_multiset_equal(
        cls,
        actual: ParsedLinearAlgebra,
        expected: ParsedLinearAlgebra,
    ) -> bool:
        """Compare vector-valued spectra as unordered symbolic multisets."""
        if actual.kind != "vector" or expected.kind != "vector" or actual.shape != expected.shape:
            return False
        unmatched = list(sp.Matrix(expected.value))
        for value in sp.Matrix(actual.value):
            for index, candidate in enumerate(unmatched):
                if cls._equal_scalar(value, candidate):
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched

    @staticmethod
    def _numeric_multiset_match(
        actual: np.ndarray,
        expected: np.ndarray,
        *,
        rtol: float = 1e-8,
        atol: float = 1e-10,
    ) -> bool:
        """Compare numeric spectra as unordered multisets, preserving multiplicity."""
        actual_values = np.asarray(actual).reshape(-1)
        expected_values = np.asarray(expected).reshape(-1)
        if actual_values.shape != expected_values.shape:
            return False

        compatible = np.isclose(
            actual_values[:, None],
            expected_values[None, :],
            rtol=rtol,
            atol=atol,
            equal_nan=False,
        )
        matched_expected: dict[int, int] = {}

        def match(actual_index: int, seen: set[int]) -> bool:
            for expected_index, is_compatible in enumerate(compatible[actual_index]):
                if not is_compatible or expected_index in seen:
                    continue
                seen.add(expected_index)
                previous_actual = matched_expected.get(expected_index)
                if previous_actual is None or match(previous_actual, seen):
                    matched_expected[expected_index] = actual_index
                    return True
            return False

        return all(match(index, set()) for index in range(actual_values.size))

    @staticmethod
    def _numeric_scalar(value: sp.Expr) -> complex | float | None:
        if not value.is_number:
            return None
        try:
            z = complex(sp.N(value, 16))
        except Exception:
            return None
        return float(z.real) if abs(z.imag) < 1e-14 else z

    @classmethod
    def _numeric_array(cls, value: ParsedLinearAlgebra) -> np.ndarray | None:
        if value.kind == "scalar":
            scalar = cls._numeric_scalar(value.value)
            return None if scalar is None else np.asarray(scalar)
        if value.kind == "vector":
            matrix = sp.Matrix(value.value)
            data = []
            for i in range(matrix.rows):
                scalar = cls._numeric_scalar(matrix[i, 0])
                if scalar is None:
                    return None
                data.append(scalar)
            return np.asarray(data)

        matrix = sp.Matrix(value.value)
        data: list[list[complex | float]] = []
        for i in range(matrix.rows):
            row = []
            for j in range(matrix.cols):
                scalar = cls._numeric_scalar(matrix[i, j])
                if scalar is None:
                    return None
                row.append(scalar)
            data.append(row)
        return np.asarray(data)

    @classmethod
    def _numpy_compare(cls, actual: ParsedLinearAlgebra, expected: Any, operation: str) -> dict[str, Any]:
        if operation == "matrix_characteristic_polynomial":
            try:
                symbol = expected["symbol"]
                coefficients = np.asarray(expected["coefficients"])
                poly = sp.Poly(actual.value, symbol)
                actual_coefficients = []
                for coefficient in poly.all_coeffs():
                    numeric = cls._numeric_scalar(coefficient)
                    if numeric is None:
                        raise TypeError("Characteristic polynomial contains non-numeric coefficients.")
                    actual_coefficients.append(numeric)
                actual_np = np.asarray(actual_coefficients)
                passed = bool(np.allclose(actual_np, coefficients, rtol=1e-9, atol=1e-10, equal_nan=False))
                return {
                    "available": True,
                    "independence_class": "DIFFERENT_ENGINE",
                    "engine": "numpy.poly",
                    "version": np.__version__,
                    "operation": operation,
                    "passed": passed,
                    "rtol": 1e-9,
                    "atol": 1e-10,
                    "max_abs_error": float(np.max(np.abs(actual_np - coefficients))),
                }
            except (KeyError, TypeError, ValueError, sp.PolynomialError) as exc:
                return {
                    "available": False,
                    "independence_class": "NOT_AVAILABLE",
                    "reason": f"Characteristic-polynomial numeric cross-check unavailable: {type(exc).__name__}: {exc}",
                }

        actual_np = cls._numeric_array(actual)
        if actual_np is None:
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Candidate contains symbolic or non-numeric entries."}

        if operation in {"vector_inner_product", "vector_norm", "vector_orthogonal"}:
            expected_value = expected["value"]
            try:
                passed = bool(np.allclose(
                    np.asarray(actual_np),
                    np.asarray(expected_value),
                    rtol=1e-9,
                    atol=1e-10,
                    equal_nan=False,
                ))
            except (TypeError, ValueError):
                passed = False
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.vdot" if operation == "vector_inner_product" and expected.get("hermitian", True) else "numpy.dot",
                "version": np.__version__,
                "operation": operation,
                "passed": passed,
                "rtol": 1e-9,
                "atol": 1e-10,
            }

        if operation == "vector_projection":
            expected_np = np.asarray(expected["value"])
            try:
                passed = bool(np.allclose(
                    actual_np.reshape(-1),
                    expected_np.reshape(-1),
                    rtol=1e-9,
                    atol=1e-10,
                    equal_nan=False,
                ))
                max_abs_error = float(np.max(np.abs(actual_np.reshape(-1) - expected_np.reshape(-1))))
            except (TypeError, ValueError):
                passed = False
                max_abs_error = None
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.vdot",
                "version": np.__version__,
                "operation": operation,
                "passed": passed,
                "max_abs_error": max_abs_error,
                "rtol": 1e-9,
                "atol": 1e-10,
            }

        if operation == "vector_gram_schmidt":
            candidate = expected.get("candidate")
            reference = expected.get("reference")
            try:
                passed = (
                    isinstance(candidate, list)
                    and isinstance(reference, list)
                    and len(candidate) == len(reference)
                    and all(
                        np.allclose(
                            np.asarray(actual_vector).reshape(-1),
                            np.asarray(reference_vector).reshape(-1),
                            rtol=1e-8,
                            atol=1e-10,
                            equal_nan=False,
                        )
                        for actual_vector, reference_vector in zip(candidate, reference)
                    )
                )
                max_abs_error = max(
                    (
                        float(np.max(np.abs(
                            np.asarray(actual_vector).reshape(-1)
                            - np.asarray(reference_vector).reshape(-1)
                        )))
                        for actual_vector, reference_vector in zip(candidate, reference)
                    ),
                    default=0.0,
                )
            except (TypeError, ValueError):
                passed = False
                max_abs_error = None
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.modified_gram_schmidt",
                "version": np.__version__,
                "operation": operation,
                "passed": passed,
                "max_abs_error": max_abs_error,
                "rtol": 1e-8,
                "atol": 1e-10,
            }

        if operation == "matrix_eigenvalues":
            expected_np = np.asarray(expected).reshape(-1)
            passed = cls._numeric_multiset_match(actual_np, expected_np)
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.linalg.eigvals",
                "version": np.__version__,
                "operation": operation,
                "passed": passed,
                "rtol": 1e-8,
                "atol": 1e-10,
            }

        if operation == "matrix_eigenvector":
            matrix_np = np.asarray(expected["matrix"])
            eigenvalue = complex(expected["eigenvalue"])
            vector_np = np.asarray(actual_np).reshape(-1)
            try:
                residual = matrix_np @ vector_np - eigenvalue * vector_np
                residual_norm = float(np.linalg.norm(residual))
                scale = max(
                    1.0,
                    float(np.linalg.norm(matrix_np, ord=2)) * float(np.linalg.norm(vector_np)),
                    abs(eigenvalue) * float(np.linalg.norm(vector_np)),
                )
                tolerance = 1e-9 + 1e-8 * scale
                eigenvalues = np.linalg.eigvals(matrix_np)
                eigenvalue_match = bool(np.any(np.isclose(eigenvalues, eigenvalue, rtol=1e-8, atol=1e-10)))
                passed = residual_norm <= tolerance and eigenvalue_match
            except (TypeError, ValueError, np.linalg.LinAlgError):
                residual_norm = None
                tolerance = None
                eigenvalue_match = False
                passed = False
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.linalg.eigvals",
                "version": np.__version__,
                "operation": operation,
                "passed": passed,
                "residual_norm": residual_norm,
                "tolerance": tolerance,
                "eigenvalue_match": eigenvalue_match,
            }

        expected_np = np.asarray(expected)
        try:
            passed = bool(np.allclose(actual_np, expected_np, rtol=1e-9, atol=1e-10, equal_nan=False))
        except (TypeError, ValueError):
            passed = False
        try:
            max_abs_error = float(np.max(np.abs(actual_np - expected_np)))
        except (TypeError, ValueError):
            max_abs_error = None
        engine = "numpy" if operation in {
            "vector_add", "vector_subtract", "vector_scalar_multiply",
            "vector_dot", "matrix_multiply", "matrix_transpose"
        } else "numpy.linalg"
        return {
            "available": True,
            "independence_class": "DIFFERENT_ENGINE",
            "engine": engine,
            "version": np.__version__,
            "operation": operation,
            "passed": passed,
            "rtol": 1e-9,
            "atol": 1e-10,
            "max_abs_error": max_abs_error,
        }

    @classmethod
    def _numpy_diagonalization_compare(cls, matrix, P, D) -> dict[str, Any]:
        a = cls._numeric_array(matrix)
        p = cls._numeric_array(P)
        d = cls._numeric_array(D)
        if a is None or p is None or d is None:
            return {
                "available": False,
                "independence_class": "NOT_AVAILABLE",
                "reason": "Diagonalization cross-check requires numeric matrix, P, and D.",
            }
        try:
            reconstructed = p @ d @ np.linalg.inv(p)
            reconstruction_error = float(np.max(np.abs(reconstructed - a)))
            diagonal_error = float(np.max(np.abs(d - np.diag(np.diag(d)))))
            independent_eigenvalues = np.linalg.eigvals(a)
            eigenvalue_match = cls._numeric_multiset_match(np.diag(d), independent_eigenvalues)
            scale = max(1.0, float(np.max(np.abs(a))))
            reconstruction_tolerance = 1e-9 + 1e-8 * scale
            passed = (
                reconstruction_error <= reconstruction_tolerance
                and diagonal_error <= 1e-10
                and eigenvalue_match
            )
        except (TypeError, ValueError, np.linalg.LinAlgError):
            reconstruction_error = None
            diagonal_error = None
            reconstruction_tolerance = None
            eigenvalue_match = False
            passed = False
        return {
            "available": True,
            "independence_class": "DIFFERENT_ENGINE",
            "engine": "numpy.linalg.eigvals",
            "version": np.__version__,
            "operation": "matrix_diagonalize",
            "passed": passed,
            "reconstruction_max_abs_error": reconstruction_error,
            "reconstruction_tolerance": reconstruction_tolerance,
            "diagonal_max_abs_error": diagonal_error,
            "eigenvalue_match": eigenvalue_match,
        }

    def _failure(self, edge, graph, start, details, message):
        elapsed = (time.perf_counter() - start) * 1000
        evidence = VerificationEvidence(
            backend=self.name, backend_version=self.version, graph_id=graph.id, edge_id=edge.id,
            input_node_ids=edge.input_nodes, output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations,
            command_invocation=f"LinearAlgebraChecker.verify_edge('{edge.id}')",
            passed=False, status=VerificationStatus.FAILED, execution_time_ms=elapsed,
            reproducibility={"sympy": sp.__version__, "numpy": np.__version__},
            metrics={"operation": details.get("operation")},
        )
        return VerificationReport(
            status=VerificationStatus.FAILED, backend=self.name, backend_version=self.version,
            execution_time_ms=elapsed, passed=False, details=details,
            error_message=message, evidence=evidence
        )

    def _success(self, edge, graph, start, details, steps):
        elapsed = (time.perf_counter() - start) * 1000
        numpy_cross = details.get("numpy_cross_check", {})
        evidence = VerificationEvidence(
            backend=self.name, backend_version=self.version, graph_id=graph.id, edge_id=edge.id,
            input_node_ids=edge.input_nodes, output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations,
            command_invocation=f"LinearAlgebraChecker.verify_edge('{edge.id}')",
            passed=True, status=VerificationStatus.SYMBOLIC_CHECKED, execution_time_ms=elapsed,
            reproducibility={"sympy": sp.__version__, "numpy": np.__version__},
            metrics={
                "operation": details.get("operation"),
                "independent_cross_check": bool(numpy_cross.get("available")),
                "independence_class": numpy_cross.get("independence_class"),
            },
        )
        return VerificationReport(
            status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name,
            backend_version=self.version, execution_time_ms=elapsed, passed=True,
            details=details, certificates=steps, evidence=evidence,
        )

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start = time.perf_counter()
        rule = edge.transformation_rule
        details = {"rule": rule, "operation": rule}
        if rule not in self._RULES:
            return self._failure(edge, graph, start, details,
                                 f"UNSUPPORTED: LinearAlgebraChecker does not implement rule '{rule}'.")

        inputs = [graph.get_node(node_id) for node_id in edge.input_nodes]
        outputs = [graph.get_node(node_id) for node_id in edge.output_nodes]
        if not inputs or any(x is None for x in inputs) or not outputs or any(x is None for x in outputs):
            return self._failure(edge, graph, start, details, "Referenced linear-algebra nodes are missing.")

        try:
            parsed_inputs = [parse_linear_algebra_expression(n.expression.raw_str) for n in inputs]
            parsed_outputs = [parse_linear_algebra_expression(n.expression.raw_str) for n in outputs]
        except LinearAlgebraParseError as exc:
            details["parse_error"] = str(exc)
            return self._failure(edge, graph, start, details, f"Malformed linear-algebra expression: {exc}")

        output = parsed_outputs[0]
        try:
            numpy_expected = None
            steps = []
            expected = None
            symbolic_passed = None

            if rule in {"vector_add", "vector_subtract"}:
                if len(parsed_inputs) != 2 or any(x.kind != "vector" for x in parsed_inputs) or output.kind != "vector":
                    raise LinearAlgebraParseError("Vector addition/subtraction requires two vectors and one vector output.")
                a, b = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if a.shape != b.shape:
                    raise ValueError(f"Vector shape mismatch: {a.shape} cannot be combined with {b.shape}.")
                expected = ParsedLinearAlgebra("vector", a + b if rule == "vector_add" else a - b)
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = na + nb if rule == "vector_add" else na - nb
                steps.append({"step": 1, "operation": rule, "input_shapes": [list(a.shape), list(b.shape)]})

            elif rule == "vector_scalar_multiply":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "vector" or output.kind != "vector":
                    raise LinearAlgebraParseError("Vector scalar multiplication requires one vector input and one vector output.")
                scalar_text = edge.parameters.get("scalar")
                if not isinstance(scalar_text, str) or not scalar_text.strip():
                    raise LinearAlgebraParseError("parameters['scalar'] is required.")
                scalar = parse_linear_algebra_expression(scalar_text)
                if scalar.kind != "scalar":
                    raise LinearAlgebraParseError("parameters['scalar'] must be scalar.")
                expected = ParsedLinearAlgebra("vector", scalar.value * sp.Matrix(parsed_inputs[0].value))
                nv, ns = self._numeric_array(parsed_inputs[0]), self._numeric_scalar(scalar.value)
                if nv is not None and ns is not None:
                    numpy_expected = ns * nv
                steps.append({"step": 1, "operation": "scalar_multiply", "scalar": str(scalar.value)})

            elif rule == "vector_dot":
                if len(parsed_inputs) != 2 or any(x.kind != "vector" for x in parsed_inputs) or output.kind != "scalar":
                    raise LinearAlgebraParseError("Vector dot product requires two vectors and one scalar output.")
                a, bb = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if a.shape != bb.shape:
                    raise ValueError(f"Vector shape mismatch: {a.shape} cannot be dotted with {bb.shape}.")
                expected = ParsedLinearAlgebra("scalar", a.dot(bb))
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = np.dot(na.reshape(-1), nb.reshape(-1))
                steps.append({"step": 1, "operation": "dot_product", "length": int(a.rows)})

            elif rule == "matrix_multiply":
                if len(parsed_inputs) != 2 or any(x.kind != "matrix" for x in parsed_inputs) or output.kind != "matrix":
                    raise LinearAlgebraParseError("Matrix multiplication requires two matrices and one matrix output.")
                a, bb = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if a.cols != bb.rows:
                    raise ValueError(f"Matrix shape mismatch: {a.shape} cannot multiply {bb.shape}.")
                expected = ParsedLinearAlgebra("matrix", a * bb)
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = na @ nb
                steps.append({"step": 1, "operation": "matrix_multiply", "lhs_shape": list(a.shape),
                              "rhs_shape": list(bb.shape), "result_shape": [int(a.rows), int(bb.cols)]})

            elif rule == "matrix_transpose":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "matrix":
                    raise LinearAlgebraParseError("Matrix transpose requires one matrix input and one matrix output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                expected = ParsedLinearAlgebra("matrix", matrix.T)
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    numpy_expected = numeric.T
                steps.append({"step": 1, "operation": "transpose", "input_shape": list(matrix.shape),
                              "result_shape": list(matrix.T.shape)})

            elif rule in {"matrix_determinant", "matrix_trace", "matrix_inverse", "matrix_rank", "matrix_rref"}:
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix":
                    raise LinearAlgebraParseError(f"{rule} requires one matrix input.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                if rule in {"matrix_determinant", "matrix_trace", "matrix_inverse"} and matrix.rows != matrix.cols:
                    raise ValueError(f"{rule} requires a square matrix; received shape {matrix.shape}.")
                numeric = self._numeric_array(parsed_inputs[0])
                if rule == "matrix_determinant":
                    expected = ParsedLinearAlgebra("scalar", matrix.det())
                    if numeric is not None: numpy_expected = np.linalg.det(numeric)
                elif rule == "matrix_trace":
                    expected = ParsedLinearAlgebra("scalar", matrix.trace())
                    if numeric is not None: numpy_expected = np.trace(numeric)
                elif rule == "matrix_inverse":
                    determinant = sp.simplify(matrix.det())
                    if determinant == 0:
                        raise ValueError("Matrix is singular; an inverse does not exist.")
                    expected = ParsedLinearAlgebra("matrix", matrix.inv())
                    if numeric is not None: numpy_expected = np.linalg.inv(numeric)
                elif rule == "matrix_rank":
                    expected = ParsedLinearAlgebra("scalar", sp.Integer(matrix.rank()))
                    if numeric is not None: numpy_expected = np.linalg.matrix_rank(numeric)
                else:
                    rref, pivots = matrix.rref()
                    expected = ParsedLinearAlgebra("matrix", rref)
                    steps.append({"step": 1, "operation": "gaussian_elimination_rref", "pivots": list(pivots)})
                if not steps:
                    steps.append({"step": 1, "operation": rule, "shape": list(matrix.shape)})

            elif rule == "vector_inner_product":
                if len(parsed_inputs) != 2 or any(x.kind != "vector" for x in parsed_inputs) or output.kind != "scalar":
                    raise LinearAlgebraParseError(
                        "vector_inner_product requires two equal-length vectors and one scalar output."
                    )
                a = sp.Matrix(parsed_inputs[0].value)
                b = sp.Matrix(parsed_inputs[1].value)
                if a.rows != b.rows:
                    raise ValueError(f"Inner-product shape mismatch: vectors have lengths {a.rows} and {b.rows}.")
                hermitian = edge.parameters.get("hermitian", True)
                if not isinstance(hermitian, bool):
                    raise LinearAlgebraParseError("parameters['hermitian'] must be boolean when provided.")
                expected_value = sp.conjugate(a).dot(b) if hermitian else a.dot(b)
                expected = ParsedLinearAlgebra("scalar", sp.simplify(expected_value))
                numeric_a = self._numeric_array(parsed_inputs[0])
                numeric_b = self._numeric_array(parsed_inputs[1])
                if numeric_a is not None and numeric_b is not None:
                    numpy_value = np.vdot(numeric_a.reshape(-1), numeric_b.reshape(-1)) if hermitian else np.dot(
                        numeric_a.reshape(-1), numeric_b.reshape(-1)
                    )
                    numpy_expected = {"value": numpy_value, "hermitian": hermitian}
                steps.append({
                    "step": 1,
                    "operation": "inner_product",
                    "hermitian": hermitian,
                    "conjugates_first_vector": hermitian,
                })

            elif rule == "vector_norm":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "vector" or output.kind != "scalar":
                    raise LinearAlgebraParseError("vector_norm requires one vector input and one scalar output.")
                vector = sp.Matrix(parsed_inputs[0].value)
                norm_squared = sp.simplify(sp.conjugate(vector).dot(vector))
                expected = ParsedLinearAlgebra("scalar", sp.sqrt(norm_squared))
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    numpy_expected = {"value": np.linalg.norm(numeric.reshape(-1))}
                steps.append({"step": 1, "operation": "euclidean_norm", "norm_squared": str(norm_squared)})

            elif rule == "vector_orthogonal":
                if len(parsed_inputs) != 2 or any(x.kind != "vector" for x in parsed_inputs) or output.kind != "scalar":
                    raise LinearAlgebraParseError(
                        "vector_orthogonal requires two equal-length vectors and a scalar indicator output."
                    )
                a = sp.Matrix(parsed_inputs[0].value)
                b = sp.Matrix(parsed_inputs[1].value)
                if a.rows != b.rows:
                    raise ValueError(f"Orthogonality shape mismatch: vectors have lengths {a.rows} and {b.rows}.")
                inner = sp.simplify(sp.conjugate(a).dot(b))
                if inner == 0:
                    expected_value = sp.Integer(1)
                elif inner.is_zero is False:
                    expected_value = sp.Integer(0)
                else:
                    return self._unverified(
                        edge,
                        graph,
                        start,
                        details,
                        "Orthogonality cannot be decided for the supplied symbolic vectors without additional assumptions.",
                    )
                expected = ParsedLinearAlgebra("scalar", expected_value)
                numeric_a = self._numeric_array(parsed_inputs[0])
                numeric_b = self._numeric_array(parsed_inputs[1])
                if numeric_a is not None and numeric_b is not None:
                    numpy_expected = {"value": np.asarray(1 if np.vdot(numeric_a.reshape(-1), numeric_b.reshape(-1)) == 0 else 0)}
                steps.append({
                    "step": 1,
                    "operation": "orthogonality",
                    "inner_product": str(inner),
                    "indicator_convention": "1=orthogonal, 0=not orthogonal",
                })

            elif rule == "vector_projection":
                if len(parsed_inputs) != 2 or any(x.kind != "vector" for x in parsed_inputs) or output.kind != "vector":
                    raise LinearAlgebraParseError(
                        "vector_projection requires a vector and a non-zero target vector, with one vector output."
                    )
                vector = sp.Matrix(parsed_inputs[0].value)
                target = sp.Matrix(parsed_inputs[1].value)
                if vector.rows != target.rows:
                    raise ValueError(f"Projection shape mismatch: vectors have lengths {vector.rows} and {target.rows}.")
                denominator = sp.simplify(sp.conjugate(target).dot(target))
                if denominator == 0:
                    raise ValueError("Cannot project onto the zero vector.")
                if denominator.is_zero is not False:
                    return self._unverified(
                        edge,
                        graph,
                        start,
                        details,
                        "Projection target non-zeroness cannot be established under the current symbolic assumptions.",
                    )
                coefficient = sp.simplify(sp.conjugate(target).dot(vector) / denominator)
                projected = sp.simplify(coefficient * target)
                expected = ParsedLinearAlgebra("vector", projected)
                numeric_vector = self._numeric_array(parsed_inputs[0])
                numeric_target = self._numeric_array(parsed_inputs[1])
                if numeric_vector is not None and numeric_target is not None:
                    denominator_np = np.vdot(numeric_target.reshape(-1), numeric_target.reshape(-1))
                    numpy_expected = {
                        "value": (
                            np.vdot(numeric_target.reshape(-1), numeric_vector.reshape(-1))
                            / denominator_np
                            * numeric_target.reshape(-1)
                        )
                    }
                steps.append({
                    "step": 1,
                    "operation": "vector_projection",
                    "target_norm_squared": str(denominator),
                    "coefficient": str(coefficient),
                })

            elif rule == "vector_gram_schmidt":
                if len(parsed_inputs) < 1 or any(x.kind != "vector" for x in parsed_inputs):
                    raise LinearAlgebraParseError("vector_gram_schmidt requires one or more vector inputs.")
                if len(parsed_outputs) != len(parsed_inputs) or any(x.kind != "vector" for x in parsed_outputs):
                    raise LinearAlgebraParseError(
                        "vector_gram_schmidt requires one output vector for each input vector."
                    )
                vectors = [sp.Matrix(x.value) for x in parsed_inputs]
                dimension = vectors[0].rows
                if any(v.rows != dimension for v in vectors):
                    raise ValueError("Gram-Schmidt requires all vectors to have the same dimension.")
                orthonormal = edge.parameters.get("orthonormal", False)
                if not isinstance(orthonormal, bool):
                    raise LinearAlgebraParseError("parameters['orthonormal'] must be boolean when provided.")
                generated = []
                for index, vector in enumerate(vectors):
                    q = vector.copy()
                    for prior in generated:
                        denominator = sp.simplify(sp.conjugate(prior).dot(prior))
                        if denominator == 0:
                            raise ValueError("Gram-Schmidt encountered a zero basis vector.")
                        if denominator.is_zero is not False:
                            return self._unverified(
                                edge,
                                graph,
                                start,
                                details,
                                "Gram-Schmidt encountered a symbolic norm that cannot be proven non-zero.",
                            )
                        coefficient = sp.simplify(sp.conjugate(prior).dot(vector) / denominator)
                        q = sp.simplify(q - coefficient * prior)
                    residual_norm_squared = sp.simplify(sp.conjugate(q).dot(q))
                    if residual_norm_squared == 0:
                        raise ValueError(
                            f"Gram-Schmidt input vector {index} is linearly dependent on the preceding vectors."
                        )
                    if residual_norm_squared.is_zero is not False:
                        return self._unverified(
                            edge,
                            graph,
                            start,
                            details,
                            "Gram-Schmidt cannot establish independence for the supplied symbolic vectors.",
                        )
                    if orthonormal:
                        q = sp.simplify(q / sp.sqrt(residual_norm_squared))
                    generated.append(q)
                expected_values = sp.Matrix.hstack(*generated)
                candidate_values = [sp.Matrix(x.value) for x in parsed_outputs]
                symbolic_passed = all(
                    self._equal(
                        ParsedLinearAlgebra("vector", candidate_values[index]),
                        ParsedLinearAlgebra("vector", generated[index]),
                    )
                    for index in range(len(generated))
                )
                numpy_inputs = [self._numeric_array(x) for x in parsed_inputs]
                if all(x is not None for x in numpy_inputs):
                    q_values = []
                    for vector in numpy_inputs:
                        q = np.asarray(vector, dtype=complex).reshape(-1).copy()
                        for prior in q_values:
                            coefficient = np.vdot(prior, q) / np.vdot(prior, prior)
                            q = q - coefficient * prior
                        if orthonormal:
                            q = q / np.linalg.norm(q)
                        q_values.append(q)
                    numpy_expected = {
                        "candidate": [self._numeric_array(x) for x in parsed_outputs],
                        "reference": q_values,
                    }
                else:
                    numpy_expected = None
                expected = ParsedLinearAlgebra("matrix", expected_values)
                steps = [
                    {
                        "step": index + 1,
                        "operation": "gram_schmidt",
                        "orthonormal": orthonormal,
                        "output_vector": index,
                    }
                    for index in range(len(generated))
                ]

            elif rule == "matrix_characteristic_polynomial":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "scalar":
                    raise LinearAlgebraParseError("matrix_characteristic_polynomial requires one square matrix input and one scalar output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"matrix_characteristic_polynomial requires a square matrix; received {matrix.shape}.")
                symbol_text = edge.parameters.get("symbol", "lam")
                if not isinstance(symbol_text, str) or not symbol_text.strip() or not symbol_text.isidentifier() or keyword.iskeyword(symbol_text):
                    raise LinearAlgebraParseError("parameters['symbol'] must be a non-keyword identifier such as 'lam'.")
                symbol = sp.Symbol(symbol_text)
                if symbol in set().union(*(entry.free_symbols for entry in matrix)):
                    raise ValueError(f"Characteristic-polynomial symbol '{symbol_text}' must not appear in matrix entries.")
                polynomial = matrix.charpoly(symbol)
                expected = ParsedLinearAlgebra("scalar", polynomial.as_expr())
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    numpy_expected = {"coefficients": np.poly(numeric), "symbol": symbol}
                steps.append({"step": 1, "operation": "characteristic_polynomial",
                              "generator": str(polynomial.gen), "degree": int(matrix.rows),
                              "convention": "det(lam*I - A)"})

            elif rule == "matrix_eigenvalues":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "vector":
                    raise LinearAlgebraParseError("matrix_eigenvalues requires one square matrix input and one vector output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"matrix_eigenvalues requires a square matrix; received {matrix.shape}.")
                try:
                    eigenvalue_map = matrix.eigenvals()
                except Exception as exc:
                    return self._unverified(edge, graph, start, details,
                                            f"SymPy could not complete the eigenvalue calculation: {type(exc).__name__}: {exc}")
                expanded = []
                for eigenvalue, multiplicity in eigenvalue_map.items():
                    expanded.extend([eigenvalue] * int(multiplicity))
                for eigenvalue in expanded:
                    try:
                        parse_linear_algebra_expression(str(eigenvalue))
                    except LinearAlgebraParseError as exc:
                        return self._unverified(edge, graph, start, details,
                                                 f"Eigenvalue {eigenvalue} is outside the current scalar representation boundary: {exc}")
                expected = ParsedLinearAlgebra("vector", sp.Matrix(expanded))
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    numpy_expected = np.linalg.eigvals(numeric)
                symbolic_passed = self._symbolic_multiset_equal(output, expected)
                steps.append({"step": 1, "operation": "eigenvalue_spectrum",
                              "algebraic_multiplicities": {str(k): int(v) for k, v in eigenvalue_map.items()},
                              "count": len(expanded)})

            elif rule == "matrix_eigenvector":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "vector":
                    raise LinearAlgebraParseError("matrix_eigenvector requires one square matrix input and one vector output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"matrix_eigenvector requires a square matrix; received {matrix.shape}.")
                eigenvalue_text = edge.parameters.get("eigenvalue")
                if not isinstance(eigenvalue_text, str) or not eigenvalue_text.strip():
                    raise LinearAlgebraParseError("parameters['eigenvalue'] is required.")
                eigenvalue = parse_linear_algebra_expression(eigenvalue_text)
                if eigenvalue.kind != "scalar":
                    raise LinearAlgebraParseError("parameters['eigenvalue'] must be scalar.")
                vector = sp.Matrix(output.value)
                if vector.rows != matrix.rows:
                    raise ValueError(f"Eigenvector shape mismatch: matrix is {matrix.shape} but candidate has length {vector.rows}.")
                if all(sp.simplify(component) == 0 for component in vector):
                    raise ValueError("An eigenvector must be non-zero.")
                residual = (matrix - eigenvalue.value * sp.eye(matrix.rows)) * vector
                residual_components = [sp.simplify(component) for component in residual]
                symbolic_passed = all(component == 0 for component in residual_components)
                details["eigenvalue"] = str(eigenvalue.value)
                details["residual"] = [str(component) for component in residual_components]
                numeric_matrix = self._numeric_array(parsed_inputs[0])
                numeric_eigenvalue = self._numeric_scalar(eigenvalue.value)
                if numeric_matrix is not None and numeric_eigenvalue is not None:
                    numpy_expected = {"matrix": numeric_matrix, "eigenvalue": numeric_eigenvalue}
                steps.append({"step": 1, "operation": "eigenvector_residual",
                              "eigenvalue": str(eigenvalue.value), "nonzero_vector": True})

            elif rule == "matrix_diagonalize":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix":
                    raise LinearAlgebraParseError("matrix_diagonalize requires one square matrix input.")
                if len(parsed_outputs) != 2 or any(x.kind != "matrix" for x in parsed_outputs):
                    raise LinearAlgebraParseError("matrix_diagonalize requires matrix outputs P and D.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                P, D = sp.Matrix(parsed_outputs[0].value), sp.Matrix(parsed_outputs[1].value)
                if matrix.rows != matrix.cols or P.shape != matrix.shape or D.shape != matrix.shape:
                    raise ValueError(f"Diagonalization requires A, P, and D to have the same square shape; received A={matrix.shape}, P={P.shape}, D={D.shape}.")
                if any(sp.simplify(D[i, j]) != 0 for i in range(D.rows) for j in range(D.cols) if i != j):
                    raise ValueError("Diagonalization candidate D is not diagonal.")
                determinant = sp.simplify(P.det())
                if determinant == 0:
                    raise ValueError("Diagonalization matrix P is singular.")
                if determinant.free_symbols:
                    return self._unverified(edge, graph, start, details,
                                            "Diagonalization requires an explicitly nonzero determinant for symbolic P; the current batch does not assume parameter domains.")
                reconstructed = P * D * P.inv()
                symbolic_passed = all(
                    self._equal_scalar(reconstructed[i, j], matrix[i, j])
                    for i in range(matrix.rows) for j in range(matrix.cols)
                )
                details["P"] = self._display(parsed_outputs[0])
                details["D"] = self._display(parsed_outputs[1])
                details["reconstruction"] = self._display(ParsedLinearAlgebra("matrix", reconstructed))
                details["determinant_P"] = str(determinant)
                details["diagonal_entries"] = [str(D[i, i]) for i in range(D.rows)]
                if self._numeric_array(parsed_inputs[0]) is not None:
                    numpy_expected = {"matrix": parsed_inputs[0], "P": parsed_outputs[0], "D": parsed_outputs[1]}
                steps = [
                    {"step": 1, "operation": "verify_diagonal_D"},
                    {"step": 2, "operation": "verify_P_invertible", "determinant": str(determinant)},
                    {"step": 3, "operation": "verify_reconstruction_A_equals_PDP_inv"},
                ]

            elif rule == "linear_system_solve":
                if len(parsed_inputs) != 2 or parsed_inputs[0].kind != "matrix" or parsed_inputs[1].kind != "vector" or output.kind != "vector":
                    raise LinearAlgebraParseError("linear_system_solve requires matrix A, vector b, and vector x.")
                matrix, vector = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"linear_system_solve requires square A; received {matrix.shape}.")
                if vector.rows != matrix.rows:
                    raise ValueError(f"Linear-system shape mismatch: A is {matrix.shape} but b has length {vector.rows}.")
                determinant = sp.simplify(matrix.det())
                if determinant == 0:
                    raise ValueError("Linear system does not have a unique solution because det(A) = 0.")
                solution = matrix.LUsolve(vector)
                augmented_rref, pivots = matrix.row_join(vector).rref()
                expected = ParsedLinearAlgebra("vector", solution)
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = np.linalg.solve(na, nb.reshape(-1))
                steps = [
                    {"step": 1, "operation": "augment_system", "shape": [int(matrix.rows), int(matrix.cols + 1)]},
                    {"step": 2, "operation": "gaussian_elimination_rref", "pivots": list(pivots),
                     "rref": [[str(augmented_rref[i, j]) for j in range(augmented_rref.cols)] for i in range(augmented_rref.rows)]},
                    {"step": 3, "operation": "back_substitution", "solution": [str(v) for v in solution]},
                ]
            else:
                raise AssertionError(f"Unhandled linear algebra rule {rule}")

            details["input_shapes"] = [list(x.shape) for x in parsed_inputs]
            if rule == "matrix_diagonalize":
                details["output_shapes"] = [list(x.shape) for x in parsed_outputs]
                details["symbolic_equivalence"] = symbolic_passed
            else:
                details["output_shape"] = list(output.shape)
                details["expected"] = None if expected is None else self._display(expected)
                details["actual"] = self._display(output)
                if symbolic_passed is None:
                    symbolic_passed = self._equal(output, expected)
                details["symbolic_equivalence"] = symbolic_passed

            if rule == "matrix_diagonalize":
                cross = self._numpy_diagonalization_compare(parsed_inputs[0], parsed_outputs[0], parsed_outputs[1])
            else:
                cross = {"available": False, "independence_class": "NOT_AVAILABLE",
                         "reason": "Inputs are symbolic or no independent numeric algorithm is configured."}
                if numpy_expected is not None:
                    cross = self._numpy_compare(output, numpy_expected, rule)
            if cross.get("available") and not cross.get("passed"):
                return self._failure(edge, graph, start, {**details, "numpy_cross_check": cross},
                                     "Independent NumPy cross-check disagreed with the candidate result.")
            details["numpy_cross_check"] = cross

            if not symbolic_passed:
                return self._failure(edge, graph, start, details,
                                     f"Linear algebra claim is incorrect for rule '{rule}'.")
            return self._success(edge, graph, start, details, steps)

        except (LinearAlgebraParseError, ValueError, TypeError, sp.ShapeError, sp.NonSquareMatrixError) as exc:
            return self._failure(edge, graph, start, details,
                                 f"Linear algebra verification failed: {type(exc).__name__}: {exc}")
        except Exception as exc:
            return self._failure(edge, graph, start, details,
                                 f"Linear algebra backend error: {type(exc).__name__}: {exc}")
