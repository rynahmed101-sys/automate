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
        "matrix_null_space", "matrix_row_space", "matrix_column_space",
        "vector_span_membership", "vector_linear_independence", "vector_basis_of_span", "vector_change_of_basis",
        "linear_transformation_apply", "matrix_representation", "matrix_svd", "matrix_pseudoinverse", "linear_least_squares",
        "matrix_positive_definite",
        "matrix_symmetric", "matrix_hermitian", "quadratic_form_evaluate",
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
                "engine": (
                    "numpy.vdot"
                    if operation == "vector_inner_product" and expected.get("hermitian", True)
                    else "numpy.dot"
                    if operation == "vector_inner_product"
                    else "numpy.linalg.norm"
                ),
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

        if operation == "quadratic_form_evaluate":
            expected_value = expected["value"]
            try:
                actual_scalar = complex(np.asarray(actual_np).reshape(()))
                expected_scalar = complex(expected_value)
                passed = bool(np.isclose(actual_scalar, expected_scalar, rtol=1e-9, atol=1e-10, equal_nan=False))
                max_abs_error = float(abs(actual_scalar - expected_scalar))
            except (TypeError, ValueError):
                passed = False
                max_abs_error = None
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": expected.get("operation", "numpy.quadratic_form"),
                "version": np.__version__,
                "operation": operation,
                "domain": expected.get("domain"),
                "passed": passed,
                "max_abs_error": max_abs_error,
                "rtol": 1e-9,
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

    @staticmethod
    def _has_free_symbols(value: ParsedLinearAlgebra) -> bool:
        if value.kind == "scalar":
            return bool(value.value.free_symbols)
        return any(entry.free_symbols for entry in sp.Matrix(value.value))

    @classmethod
    def _numpy_subspace_compare(
        cls, rule: str, parsed_inputs: list[ParsedLinearAlgebra], parsed_outputs: list[ParsedLinearAlgebra]
    ) -> dict[str, Any]:
        """Independently verify subspace dimensions/residuals with NumPy."""
        arrays = [cls._numeric_array(value) for value in [*parsed_inputs, *parsed_outputs]]
        if any(value is None for value in arrays):
            return {
                "available": False,
                "independence_class": "NOT_AVAILABLE",
                "reason": "Subspace cross-check requires numeric inputs and outputs.",
            }
        inputs = arrays[:len(parsed_inputs)]
        outputs = arrays[len(parsed_inputs):]
        candidate = outputs[0]
        try:
            if rule == "matrix_null_space":
                matrix = inputs[0]
                expected_dim = matrix.shape[1] - np.linalg.matrix_rank(matrix)
                residual = matrix @ candidate
                scale = max(1.0, float(np.linalg.norm(matrix, ord=np.inf)) * float(np.linalg.norm(candidate, ord=np.inf)) if candidate.size else 1.0)
                tolerance = 1e-9 + 1e-8 * scale
                candidate_rank = np.linalg.matrix_rank(candidate)
                residual_ok = residual.size == 0 or float(np.max(np.abs(residual))) <= tolerance
                passed = residual_ok and candidate_rank == expected_dim
                metric = {"residual_max_abs": float(np.max(np.abs(residual))) if residual.size else 0.0}
            elif rule == "matrix_row_space":
                matrix = inputs[0]
                if candidate.shape[0] != matrix.shape[1]:
                    passed = False
                    metric = {"shape_match": False}
                else:
                    rank_a = np.linalg.matrix_rank(matrix)
                    rank_c = np.linalg.matrix_rank(candidate)
                    combined = np.vstack([matrix.T, candidate])
                    combined_rank = np.linalg.matrix_rank(combined)
                    passed = rank_c == rank_a == combined_rank
                    metric = {"rank_input": int(rank_a), "rank_candidate": int(rank_c), "rank_combined": int(combined_rank)}
            elif rule == "matrix_column_space":
                matrix = inputs[0]
                if candidate.shape[0] != matrix.shape[0]:
                    passed = False
                    metric = {"shape_match": False}
                else:
                    rank_a = np.linalg.matrix_rank(matrix)
                    rank_c = np.linalg.matrix_rank(candidate)
                    combined = np.hstack([matrix, candidate])
                    combined_rank = np.linalg.matrix_rank(combined)
                    passed = rank_c == rank_a == combined_rank
                    metric = {"rank_input": int(rank_a), "rank_candidate": int(rank_c), "rank_combined": int(combined_rank)}
            elif rule == "vector_span_membership":
                generators, vector = inputs
                if generators.shape[0] != vector.reshape(-1).shape[0]:
                    passed = False
                    metric = {"shape_match": False}
                else:
                    rank_g = np.linalg.matrix_rank(generators)
                    rank_aug = np.linalg.matrix_rank(np.column_stack([generators, vector.reshape(-1)]))
                    passed = rank_g == rank_aug
                    metric = {"rank_generators": int(rank_g), "rank_augmented": int(rank_aug)}
            elif rule == "vector_linear_independence":
                generators = inputs[0]
                rank_g = np.linalg.matrix_rank(generators)
                passed = rank_g == generators.shape[1]
                metric = {"rank": int(rank_g), "column_count": int(generators.shape[1])}
            
            elif rule == "vector_change_of_basis":
                source_basis, target_basis, source_coords = inputs
                candidate = outputs[0]
                if source_basis.ndim != 2 or target_basis.ndim != 2 or source_basis.shape != target_basis.shape:
                    passed = False
                    metric = {"shape_match": False}
                elif source_basis.shape[0] != source_basis.shape[1] or source_coords.reshape(-1).shape[0] != source_basis.shape[1]:
                    passed = False
                    metric = {"basis_and_coordinate_shapes_valid": False}
                else:
                    try:
                        physical = source_basis @ source_coords.reshape(-1)
                        expected_coords = np.linalg.solve(target_basis, physical)
                        candidate = np.asarray(candidate).reshape(-1)
                        scale = max(1.0, float(np.max(np.abs(expected_coords))) if expected_coords.size else 1.0)
                        residual = float(np.max(np.abs(candidate - expected_coords))) if candidate.shape == expected_coords.shape else float("inf")
                        tolerance = 1e-9 + 1e-8 * scale
                        passed = residual <= tolerance
                        metric = {"residual_max_abs": residual, "tolerance": tolerance, "source_dimension": int(source_basis.shape[0])}
                    except np.linalg.LinAlgError:
                        passed = False
                        metric = {"target_basis_invertible": False}
            else:
                generators, basis = inputs
                rank_g = np.linalg.matrix_rank(generators)
                rank_b = np.linalg.matrix_rank(basis)
                combined = np.column_stack([generators, basis])
                combined_rank = np.linalg.matrix_rank(combined)
                passed = rank_b == rank_g == combined_rank
                metric = {"rank_generators": int(rank_g), "rank_basis": int(rank_b), "rank_combined": int(combined_rank)}
            return {
                "available": True,
                "independence_class": "DIFFERENT_ENGINE",
                "engine": "numpy.linalg.matrix_rank",
                "version": np.__version__,
                "operation": rule,
                "passed": bool(passed),
                "rtol": 1e-8,
                "atol": 1e-10,
                **metric,
            }
        except (TypeError, ValueError, np.linalg.LinAlgError) as exc:
            return {
                "available": False,
                "independence_class": "NOT_AVAILABLE",
                "reason": f"NumPy subspace cross-check unavailable: {type(exc).__name__}: {exc}",
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

    def _unverified(self, edge, graph, start, details, message):
        elapsed = (time.perf_counter() - start) * 1000
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            graph_id=graph.id,
            edge_id=edge.id,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations,
            command_invocation=f"LinearAlgebraChecker.verify_edge('{edge.id}')",
            passed=False,
            status=VerificationStatus.UNVERIFIED,
            execution_time_ms=elapsed,
            reproducibility={"sympy": sp.__version__, "numpy": np.__version__},
            metrics={"operation": details.get("operation")},
        )
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=False,
            details=details,
            error_message=message,
            evidence=evidence,
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
                    inner_numeric = np.vdot(numeric_a.reshape(-1), numeric_b.reshape(-1))
                    numpy_expected = {
                        "value": np.asarray(
                            1 if np.isclose(inner_numeric, 0, rtol=1e-9, atol=1e-10) else 0
                        )
                    }
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

            elif rule in {"matrix_null_space", "matrix_row_space", "matrix_column_space"}:
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "matrix":
                    raise LinearAlgebraParseError(f"{rule} requires one matrix input and one matrix output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                candidate = sp.Matrix(output.value)
                if self._has_free_symbols(parsed_inputs[0]) or self._has_free_symbols(output):
                    return self._unverified(
                        edge, graph, start, details,
                        "Subspace basis verification is restricted to explicit scalar entries; symbolic parameter domains are not inferred."
                    )
                if rule == "matrix_null_space":
                    if candidate.rows != matrix.cols:
                        raise ValueError(f"Null-space basis must have {matrix.cols} rows; received {candidate.shape}.")
                    residual = matrix * candidate
                    target_rank = matrix.cols - matrix.rank()
                    candidate_rank = candidate.rank()
                    symbolic_passed = (
                        all(sp.simplify(value) == 0 for value in residual)
                        and candidate_rank == target_rank
                    )
                    steps = [
                        {"step": 1, "operation": "verify_null_space_residual", "residual": self._display(ParsedLinearAlgebra("matrix", residual))},
                        {"step": 2, "operation": "verify_nullity_basis_dimension", "expected_dimension": int(target_rank), "candidate_rank": int(candidate_rank)},
                    ]
                elif rule == "matrix_row_space":
                    # Represent row-space basis vectors as columns so zero-dimensional
                    # row spaces remain representable as an n x 0 matrix.
                    if candidate.rows != matrix.cols:
                        raise ValueError(f"Row-space basis must have {matrix.cols} rows; received {candidate.shape}.")
                    rank_a = matrix.rank()
                    rank_c = candidate.rank()
                    combined_rank = matrix.T.row_join(candidate).rank()
                    symbolic_passed = rank_c == rank_a == combined_rank
                    steps = [
                        {"step": 1, "operation": "verify_row_space_basis_rank", "input_rank": int(rank_a), "candidate_rank": int(rank_c), "combined_rank": int(combined_rank)},
                    ]
                else:
                    if candidate.rows != matrix.rows:
                        raise ValueError(f"Column-space basis must have {matrix.rows} rows; received {candidate.shape}.")
                    rank_a = matrix.rank()
                    rank_c = candidate.rank()
                    combined_rank = matrix.row_join(candidate).rank()
                    symbolic_passed = rank_c == rank_a == combined_rank
                    steps = [
                        {"step": 1, "operation": "verify_column_space_basis_rank", "input_rank": int(rank_a), "candidate_rank": int(rank_c), "combined_rank": int(combined_rank)},
                    ]
                expected = output
                numpy_expected = None

            elif rule == "vector_span_membership":
                if len(parsed_inputs) != 2 or parsed_inputs[0].kind != "matrix" or parsed_inputs[1].kind != "vector" or output.kind != "scalar":
                    raise LinearAlgebraParseError("vector_span_membership requires a generator matrix, candidate vector, and scalar indicator.")
                generators = sp.Matrix(parsed_inputs[0].value)
                vector = sp.Matrix(parsed_inputs[1].value)
                if self._has_free_symbols(parsed_inputs[0]) or self._has_free_symbols(parsed_inputs[1]):
                    return self._unverified(
                        edge, graph, start, details,
                        "Span membership is restricted to explicit scalar entries; symbolic parameter domains are not inferred."
                    )
                if generators.rows != vector.rows:
                    raise ValueError(f"Span membership shape mismatch: generator matrix has {generators.rows} rows but candidate has length {vector.rows}.")
                rank_generators = generators.rank()
                rank_augmented = generators.row_join(vector).rank()
                expected_value = sp.Integer(1 if rank_generators == rank_augmented else 0)
                expected = ParsedLinearAlgebra("scalar", expected_value)
                steps = [{"step": 1, "operation": "span_membership_rank_test", "generator_rank": int(rank_generators), "augmented_rank": int(rank_augmented)}]
                numeric_g = self._numeric_array(parsed_inputs[0])
                numeric_v = self._numeric_array(parsed_inputs[1])
                if numeric_g is not None and numeric_v is not None:
                    numpy_expected = {"generators": numeric_g, "vector": numeric_v}
                    # Candidate indicator is checked by the dedicated subspace cross-check below.

            elif rule == "vector_linear_independence":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "scalar":
                    raise LinearAlgebraParseError("vector_linear_independence requires a generator matrix whose columns are vectors and a scalar indicator.")
                generators = sp.Matrix(parsed_inputs[0].value)
                if self._has_free_symbols(parsed_inputs[0]):
                    return self._unverified(
                        edge, graph, start, details,
                        "Linear-independence verification is restricted to explicit scalar entries; symbolic parameter domains are not inferred."
                    )
                rank_generators = generators.rank()
                expected = ParsedLinearAlgebra("scalar", sp.Integer(1 if rank_generators == generators.cols else 0))
                steps = [{"step": 1, "operation": "linear_independence_rank_test", "rank": int(rank_generators), "vector_count": int(generators.cols)}]
                numeric_g = self._numeric_array(parsed_inputs[0])
                if numeric_g is not None:
                    numpy_expected = {"generators": numeric_g}

            elif rule == "vector_basis_of_span":
                if len(parsed_inputs) != 2 or any(x.kind != "matrix" for x in parsed_inputs) or output.kind != "scalar":
                    raise LinearAlgebraParseError("vector_basis_of_span requires a generator matrix, candidate basis matrix, and scalar indicator.")
                generators = sp.Matrix(parsed_inputs[0].value)
                basis = sp.Matrix(parsed_inputs[1].value)
                if generators.rows != basis.rows:
                    raise ValueError(f"Basis shape mismatch: generator matrix has {generators.rows} rows but candidate basis has {basis.rows}.")
                if self._has_free_symbols(parsed_inputs[0]) or self._has_free_symbols(parsed_inputs[1]):
                    return self._unverified(
                        edge, graph, start, details,
                        "Basis verification is restricted to explicit scalar entries; symbolic parameter domains are not inferred."
                    )
                rank_generators = generators.rank()
                rank_basis = basis.rank()
                combined_rank = generators.row_join(basis).rank()
                expected = ParsedLinearAlgebra("scalar", sp.Integer(1 if rank_basis == rank_generators == combined_rank else 0))
                steps = [{"step": 1, "operation": "basis_span_rank_test", "generator_rank": int(rank_generators), "basis_rank": int(rank_basis), "combined_rank": int(combined_rank)}]
                numeric_g = self._numeric_array(parsed_inputs[0])
                numeric_b = self._numeric_array(parsed_inputs[1])
                if numeric_g is not None and numeric_b is not None:
                    numpy_expected = {"generators": numeric_g, "basis": numeric_b}

            elif rule == "linear_transformation_apply":
                if len(parsed_inputs) != 2 or parsed_inputs[0].kind != "matrix" or parsed_inputs[1].kind != "vector" or output.kind != "vector":
                    raise LinearAlgebraParseError(
                        "linear_transformation_apply requires a transformation matrix, input vector, and output vector."
                    )
                transformation = sp.Matrix(parsed_inputs[0].value)
                vector = sp.Matrix(parsed_inputs[1].value)
                candidate = sp.Matrix(output.value)
                if transformation.cols != vector.rows:
                    raise ValueError(
                        f"Linear-transformation shape mismatch: matrix {transformation.shape} cannot act on vector length {vector.rows}."
                    )
                if candidate.rows != transformation.rows:
                    raise ValueError(
                        f"Linear-transformation output mismatch: expected length {transformation.rows}, received {candidate.rows}."
                    )
                expected = ParsedLinearAlgebra("vector", transformation * vector)
                numeric_matrix = self._numeric_array(parsed_inputs[0])
                numeric_vector = self._numeric_array(parsed_inputs[1])
                if numeric_matrix is not None and numeric_vector is not None:
                    numpy_expected = numeric_matrix @ numeric_vector.reshape(-1)
                steps.append({
                    "step": 1,
                    "operation": "linear_transformation_matrix_action",
                    "domain_dimension": int(transformation.cols),
                    "codomain_dimension": int(transformation.rows),
                })

            elif rule == "matrix_representation":
                if len(parsed_inputs) != 2 or any(x.kind != "matrix" for x in parsed_inputs) or output.kind != "matrix":
                    raise LinearAlgebraParseError(
                        "matrix_representation requires a domain-basis matrix, its image matrix, and a candidate representation matrix."
                    )
                basis = sp.Matrix(parsed_inputs[0].value)
                images = sp.Matrix(parsed_inputs[1].value)
                candidate = sp.Matrix(output.value)
                if basis.rows != basis.cols:
                    raise ValueError(
                        f"matrix_representation requires a square full-domain basis matrix; received {basis.shape}."
                    )
                if images.cols != basis.cols:
                    raise ValueError(
                        f"Basis-image mismatch: basis has {basis.cols} vectors but images contain {images.cols} columns."
                    )
                if candidate.shape != (images.rows, basis.rows):
                    raise ValueError(
                        f"Representation shape mismatch: expected {(images.rows, basis.rows)}, received {candidate.shape}."
                    )
                determinant = sp.simplify(basis.det())
                if determinant == 0:
                    raise ValueError("The supplied domain basis is singular and cannot represent a full basis.")
                if determinant.free_symbols:
                    return self._unverified(
                        edge,
                        graph,
                        start,
                        details,
                        "Basis invertibility cannot be established for symbolic parameters without explicit domain assumptions.",
                    )
                expected_matrix = sp.simplify(images * basis.inv())
                expected = ParsedLinearAlgebra("matrix", expected_matrix)
                numeric_basis = self._numeric_array(parsed_inputs[0])
                numeric_images = self._numeric_array(parsed_inputs[1])
                if numeric_basis is not None and numeric_images is not None:
                    try:
                        numpy_expected = numeric_images @ np.linalg.inv(numeric_basis)
                    except np.linalg.LinAlgError as exc:
                        return self._failure(edge, graph, start, details, f"Independent matrix-representation cross-check failed: {exc}")
                steps = [
                    {"step": 1, "operation": "verify_basis_invertibility", "determinant": str(determinant)},
                    {"step": 2, "operation": "reconstruct_matrix_from_basis_images", "relation": "M * B = C"},
                ]

            elif rule in {"matrix_symmetric", "matrix_hermitian"}:
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "scalar":
                    raise LinearAlgebraParseError(
                        f"{rule} requires one square matrix input and one scalar indicator output."
                    )
                matrix = sp.Matrix(parsed_inputs[0].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"{rule} requires a square matrix; received {matrix.shape}.")
                if rule == "matrix_symmetric":
                    residual = matrix - matrix.T
                    property_name = "symmetric"
                else:
                    residual = matrix - matrix.conjugate().T
                    property_name = "Hermitian"
                simplified = [sp.simplify(value) for value in residual]
                if all(value == 0 for value in simplified):
                    expected_value = sp.Integer(1)
                elif any(value.is_zero is False for value in simplified):
                    expected_value = sp.Integer(0)
                else:
                    return self._unverified(
                        edge, graph, start, details,
                        f"{property_name} status cannot be decided for the supplied symbolic matrix without additional assumptions."
                    )
                expected = ParsedLinearAlgebra("scalar", expected_value)
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    matrix_np = np.asarray(numeric)
                    numpy_expected = int(np.allclose(
                        matrix_np,
                        matrix_np.T if rule == "matrix_symmetric" else matrix_np.conjugate().T,
                        rtol=1e-9,
                        atol=1e-10,
                        equal_nan=False,
                    ))
                steps = [{
                    "step": 1,
                    "operation": property_name.lower() + "_matrix_test",
                    "indicator_convention": "1=property holds, 0=property does not hold",
                }]

            elif rule == "matrix_positive_definite":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "scalar":
                    raise LinearAlgebraParseError(
                        "matrix_positive_definite requires one square matrix input and one scalar indicator output."
                    )
                matrix = sp.Matrix(parsed_inputs[0].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"matrix_positive_definite requires a square matrix; received {matrix.shape}.")
                hermitian_residual = matrix - matrix.conjugate().T
                hermitian_components = [sp.simplify(value) for value in hermitian_residual]
                if any(value.is_zero is False for value in hermitian_components):
                    expected_value = sp.Integer(0)
                    hermitian_verified = False
                elif any(value != 0 for value in hermitian_components):
                    return self._unverified(edge, graph, start, details,
                        "Positive-definiteness requires a symmetric/Hermitian matrix, but the Hermitian condition cannot be established for the supplied symbolic entries.")
                else:
                    hermitian_verified = True
                    principal_minors = []
                    for size in range(1, matrix.rows + 1):
                        minor = sp.simplify(matrix[:size, :size].det())
                        principal_minors.append(minor)
                        positive = sp.ask(sp.Q.positive(minor))
                        if positive is False:
                            expected_value = sp.Integer(0)
                            break
                        if positive is not True:
                            return self._unverified(edge, graph, start, details,
                                f"Positive-definiteness cannot be established because leading principal minor {size} is not provably positive.")
                    else:
                        expected_value = sp.Integer(1)
                expected = ParsedLinearAlgebra("scalar", expected_value)
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    matrix_np = np.asarray(numeric)
                    if not hermitian_verified:
                        # eigvalsh is only valid for Hermitian/symmetric inputs. For a
                        # non-Hermitian matrix, positive definiteness is rejected by
                        # definition rather than feeding invalid input to that routine.
                        numpy_expected = 0
                    else:
                        try:
                            eigenvalues = np.linalg.eigvalsh(matrix_np)
                            scale = max(1.0, float(np.linalg.norm(matrix_np, ord=2)))
                            tolerance = 1e-10 * scale
                            numpy_expected = int(bool(np.min(eigenvalues) > tolerance))
                        except np.linalg.LinAlgError:
                            numpy_expected = None
                steps = [{"step": 1, "operation": "verify_hermitian_or_symmetric",
                          "verified": hermitian_verified if "hermitian_verified" in locals() else False}]
                if expected_value == 1:
                    steps.append({"step": 2, "operation": "sylvester_criterion",
                                  "leading_principal_minors": [str(value) for value in principal_minors]})

            elif rule == "quadratic_form_evaluate":
                if len(parsed_inputs) != 2 or parsed_inputs[0].kind != "matrix" or parsed_inputs[1].kind != "vector" or output.kind != "scalar":
                    raise LinearAlgebraParseError("quadratic_form_evaluate requires one square matrix, one vector, and one scalar output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                vector = sp.Matrix(parsed_inputs[1].value)
                if matrix.rows != matrix.cols:
                    raise ValueError(f"Quadratic-form matrix must be square; received {matrix.shape}.")
                if vector.rows != matrix.cols:
                    raise ValueError(f"Quadratic-form dimension mismatch: matrix is {matrix.shape}, vector has length {vector.rows}.")
                domain = edge.parameters.get("domain", "complex")
                if domain not in {"real", "complex"}:
                    raise LinearAlgebraParseError("parameters['domain'] must be 'real' or 'complex'.")
                require_hermitian = edge.parameters.get("require_hermitian", False)
                if not isinstance(require_hermitian, bool):
                    raise LinearAlgebraParseError("parameters['require_hermitian'] must be boolean when provided.")
                if require_hermitian:
                    residual = matrix - matrix.conjugate().T
                    simplified = [sp.simplify(value) for value in residual]
                    if all(value == 0 for value in simplified):
                        hermitian_status = "verified"
                    elif any(value.is_zero is False for value in simplified):
                        raise ValueError("Quadratic-form Hermitian requirement is false for the supplied matrix.")
                    else:
                        return self._unverified(edge, graph, start, details, "Hermitian requirement cannot be established from the supplied symbolic matrix without additional assumptions.")
                else:
                    hermitian_status = "not_required"
                if domain == "real":
                    expected_value = sp.simplify(vector.T * matrix * vector)[0]
                    numpy_operation = "numpy.dot_real_quadratic_form"
                else:
                    expected_value = sp.simplify(vector.conjugate().T * matrix * vector)[0]
                    numpy_operation = "numpy.conjugate_dot_complex_quadratic_form"
                expected = ParsedLinearAlgebra("scalar", expected_value)
                numeric_matrix = self._numeric_array(parsed_inputs[0])
                numeric_vector = self._numeric_array(parsed_inputs[1])
                if numeric_matrix is not None and numeric_vector is not None:
                    a_np = np.asarray(numeric_matrix)
                    x_np = np.asarray(numeric_vector).reshape(-1)
                    try:
                        numpy_value = np.dot(x_np, a_np @ x_np) if domain == "real" else np.conjugate(x_np) @ (a_np @ x_np)
                        numpy_expected = {"value": numpy_value, "domain": domain, "operation": numpy_operation}
                    except (TypeError, ValueError):
                        numpy_expected = None
                steps = [
                    {"step": 1, "operation": "validate_square_matrix_and_vector_dimension", "matrix_shape": list(matrix.shape), "vector_shape": list(vector.shape)},
                    {"step": 2, "operation": "select_quadratic_form_semantics", "domain": domain, "left_factor": "x.T" if domain == "real" else "x.conjugate().T"},
                    {"step": 3, "operation": "evaluate_x_star_A_x", "hermitian_requirement": require_hermitian, "hermitian_status": hermitian_status},
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

            elif rule == "matrix_pseudoinverse":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or output.kind != "matrix":
                    raise LinearAlgebraParseError("matrix_pseudoinverse requires one matrix input and one matrix output.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                candidate = sp.Matrix(output.value)
                if matrix.rows == 0 or matrix.cols == 0:
                    raise ValueError("Moore-Penrose pseudoinverse requires a non-empty matrix.")
                expected_shape = (matrix.cols, matrix.rows)
                if candidate.shape != expected_shape:
                    raise ValueError(f"Moore-Penrose pseudoinverse shape mismatch: expected {expected_shape}, got {candidate.shape}.")
                penrose_residuals = [
                    matrix * candidate * matrix - matrix,
                    candidate * matrix * candidate - candidate,
                    (matrix * candidate).conjugate().T - matrix * candidate,
                    (candidate * matrix).conjugate().T - candidate * matrix,
                ]
                labels = ["AA+ A = A", "A+ A A+ = A+", "(AA+)^H = AA+", "(A+A)^H = A+A"]
                symbolic_passed = True
                residual_details = {}
                for label, residual in zip(labels, penrose_residuals):
                    values = [sp.simplify(value) for value in residual]
                    residual_details[label] = [[str(residual[i, j]) for j in range(residual.cols)] for i in range(residual.rows)]
                    if any(value.is_zero is False for value in values):
                        symbolic_passed = False
                    elif any(value.is_zero is None for value in values):
                        return self._unverified(edge, graph, start, details, f"Moore-Penrose condition '{label}' cannot be decided exactly from the supplied symbolic expressions.")
                expected = None
                numeric = self._numeric_array(parsed_inputs[0])
                if numeric is not None:
                    numpy_expected = np.linalg.pinv(numeric)
                details["penrose_residuals"] = residual_details
                details["candidate_shape"] = list(candidate.shape)
                steps = [{"step": i + 1, "operation": "verify_moore_penrose_condition", "condition": label} for i, label in enumerate(labels)]

            elif rule == "linear_least_squares":
                if len(parsed_inputs) != 2 or parsed_inputs[0].kind != "matrix" or parsed_inputs[1].kind != "vector" or output.kind != "vector":
                    raise LinearAlgebraParseError("linear_least_squares requires matrix A, vector b, and vector x.")
                matrix = sp.Matrix(parsed_inputs[0].value)
                vector = sp.Matrix(parsed_inputs[1].value)
                candidate = sp.Matrix(output.value)
                if matrix.rows == 0 or matrix.cols == 0:
                    raise ValueError("Least-squares requires a non-empty matrix A.")
                if vector.rows != matrix.rows:
                    raise ValueError(f"Least-squares shape mismatch: A is {matrix.shape} but b has length {vector.rows}.")
                if candidate.rows != matrix.cols:
                    raise ValueError(f"Least-squares candidate must have length {matrix.cols}; got {candidate.rows}.")
                residual = sp.simplify(matrix * candidate - vector)
                normal_residual = sp.simplify(matrix.conjugate().T * residual)
                normal_values = [sp.simplify(value) for value in normal_residual]
                if any(value.is_zero is False for value in normal_values):
                    symbolic_passed = False
                elif any(value.is_zero is None for value in normal_values):
                    return self._unverified(edge, graph, start, details, "Least-squares optimality cannot be decided exactly from the supplied symbolic normal-equation residual.")
                else:
                    symbolic_passed = True
                nullspace = matrix.nullspace()
                minimum_norm_residuals = [sp.simplify(sp.conjugate(null_vector).dot(candidate)) for null_vector in nullspace]
                minimum_values = [sp.simplify(value) for value in minimum_norm_residuals]
                if any(value.is_zero is False for value in minimum_values):
                    symbolic_passed = False
                elif any(value.is_zero is None for value in minimum_values):
                    return self._unverified(edge, graph, start, details, "Minimum-norm least-squares membership in range(A^H) cannot be decided exactly from the supplied symbolic expressions.")
                expected = None
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = np.linalg.pinv(na) @ nb.reshape(-1)
                details["normal_residual"] = [str(v) for v in normal_residual]
                details["minimum_norm_residual"] = [str(v) for v in minimum_norm_residuals]
                steps = [
                    {"step": 1, "operation": "verify_normal_equations", "normal_residual": [str(v) for v in normal_residual]},
                    {"step": 2, "operation": "verify_minimum_norm_range_A_H", "nullspace_orthogonality": [str(v) for v in minimum_norm_residuals]},
                    {"step": 3, "operation": "report_residual", "residual": [str(v) for v in residual]},
                ]

            elif rule == "vector_change_of_basis":
                if len(parsed_inputs) != 3 or any(x.kind != "matrix" for x in parsed_inputs[:2]) or parsed_inputs[2].kind != "vector" or output.kind != "vector":
                    raise LinearAlgebraParseError("vector_change_of_basis requires source basis, target basis, source coordinates, and target coordinates.")
                source_basis = sp.Matrix(parsed_inputs[0].value)
                target_basis = sp.Matrix(parsed_inputs[1].value)
                source_coords = sp.Matrix(parsed_inputs[2].value)
                candidate = sp.Matrix(output.value)
                if source_basis.rows != source_basis.cols or target_basis.rows != target_basis.cols:
                    raise ValueError("Change of basis requires square basis matrices.")
                if source_basis.shape != target_basis.shape:
                    raise ValueError("Source and target bases must have the same dimension.")
                if source_coords.rows != source_basis.cols:
                    raise ValueError(f"Source coordinate vector has length {source_coords.rows}; expected {source_basis.cols}.")
                if candidate.rows != target_basis.cols:
                    raise ValueError(f"Target coordinate vector has length {candidate.rows}; expected {target_basis.cols}.")
                source_det = sp.simplify(source_basis.det())
                target_det = sp.simplify(target_basis.det())
                if source_det == 0 or target_det == 0:
                    raise ValueError("Both basis matrices must be invertible.")
                if source_det.free_symbols or target_det.free_symbols:
                    return self._unverified(edge, graph, start, details, "Change-of-basis verification requires explicitly nonzero basis determinants; parameter domains are not inferred.")
                physical_vector = source_basis * source_coords
                expected_coords = sp.simplify(target_basis.inv() * physical_vector)
                expected = ParsedLinearAlgebra("vector", expected_coords)
                numeric_source = self._numeric_array(parsed_inputs[0])
                numeric_target = self._numeric_array(parsed_inputs[1])
                numeric_coords = self._numeric_array(parsed_inputs[2])
                if numeric_source is not None and numeric_target is not None and numeric_coords is not None:
                    try:
                        numpy_expected = np.linalg.solve(numeric_target, numeric_source @ numeric_coords.reshape(-1))
                    except np.linalg.LinAlgError as exc:
                        return self._failure(edge, graph, start, details, f"Independent change-of-basis cross-check failed: {exc}")
                steps = [
                    {"step": 1, "operation": "reconstruct_physical_vector", "source_basis_determinant": str(source_det)},
                    {"step": 2, "operation": "solve_target_basis_coordinates", "target_basis_determinant": str(target_det)},
                ]

            elif rule == "matrix_svd":
                if len(parsed_inputs) != 1 or parsed_inputs[0].kind != "matrix" or len(parsed_outputs) != 3:
                    raise LinearAlgebraParseError("matrix_svd requires one input matrix and three outputs: U, Sigma, Vh.")
                A = sp.Matrix(parsed_inputs[0].value)
                U, Sigma, Vh = [sp.Matrix(value.value) for value in parsed_outputs]
                m, n = A.rows, A.cols
                k = min(m, n)
                expected_shapes = [(m, k), (k, k), (k, n)]
                actual_shapes = [(U.rows, U.cols), (Sigma.rows, Sigma.cols), (Vh.rows, Vh.cols)]
                if actual_shapes != expected_shapes:
                    raise ValueError(f"Reduced SVD shape mismatch: expected U/Sigma/Vh shapes {expected_shapes}, got {actual_shapes}.")
                identity = sp.eye(k)
                reconstruction = U * Sigma * Vh
                left_orthogonality = sp.simplify(U.conjugate().T * U - identity)
                right_orthogonality = sp.simplify(Vh * Vh.conjugate().T - identity)
                for i in range(k):
                    for j in range(k):
                        if i != j and sp.simplify(Sigma[i, j]) != 0:
                            raise ValueError("Sigma must be diagonal in the reduced SVD representation.")
                undecidable = False
                for i in range(k):
                    sigma = sp.simplify(Sigma[i, i])
                    if sigma.is_real is False or sigma.is_nonnegative is False:
                        raise ValueError("Singular values must be real and non-negative.")
                    if sigma.is_real is None or sigma.is_nonnegative is None:
                        undecidable = True
                    if i + 1 < k:
                        comparison = sp.ask(sp.Q.ge(sigma, sp.simplify(Sigma[i + 1, i + 1])))
                        if comparison is False:
                            raise ValueError("Singular values must be ordered non-increasingly.")
                        if comparison is None:
                            undecidable = True
                reconstruction_ok = all(self._equal_scalar(reconstruction[i, j], A[i, j]) for i in range(m) for j in range(n))
                left_ok = all(sp.simplify(left_orthogonality[i, j]) == 0 for i in range(k) for j in range(k))
                right_ok = all(sp.simplify(right_orthogonality[i, j]) == 0 for i in range(k) for j in range(k))
                symbolic_passed = reconstruction_ok and left_ok and right_ok
                if not symbolic_passed:
                    raise ValueError("SVD reconstruction or orthogonality condition failed.")
                details["output_shapes"] = [list(shape) for shape in actual_shapes]
                details["reconstruction"] = self._display(ParsedLinearAlgebra("matrix", reconstruction))
                details["singular_values"] = [str(Sigma[i, i]) for i in range(k)]
                details["orthogonality"] = {"U_H_U": left_ok, "Vh_Vh_H": right_ok}
                if undecidable:
                    return self._unverified(edge, graph, start, details, "SVD candidate is structurally valid, but exact singular-value non-negativity/order could not be established symbolically.")
                steps = [
                    {"step": 1, "operation": "validate_reduced_dimensions", "k": k},
                    {"step": 2, "operation": "verify_sigma_diagonal_nonnegative_ordered"},
                    {"step": 3, "operation": "verify_U_conjugate_transpose_U_equals_I"},
                    {"step": 4, "operation": "verify_Vh_Vh_conjugate_transpose_equals_I"},
                    {"step": 5, "operation": "verify_reconstruction_A_equals_U_Sigma_Vh"},
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
            if rule in {"matrix_diagonalize", "vector_gram_schmidt"}:
                details["output_shapes"] = [list(x.shape) for x in parsed_outputs]
                details["symbolic_equivalence"] = symbolic_passed
            else:
                details["output_shape"] = list(output.shape)
                details["expected"] = None if expected is None else self._display(expected)
                details["actual"] = self._display(output)
                if symbolic_passed is None:
                    symbolic_passed = self._equal(output, expected)
                details["symbolic_equivalence"] = symbolic_passed

            if rule in {"matrix_null_space", "matrix_row_space", "matrix_column_space"}:
                cross = self._numpy_subspace_compare(rule, parsed_inputs, parsed_outputs)
            elif rule == "vector_span_membership":
                numeric_g = self._numeric_array(parsed_inputs[0])
                numeric_v = self._numeric_array(parsed_inputs[1])
                if numeric_g is not None and numeric_v is not None:
                    rank_g = np.linalg.matrix_rank(numeric_g)
                    rank_aug = np.linalg.matrix_rank(np.column_stack([numeric_g, numeric_v.reshape(-1)]))
                    expected_indicator = 1 if rank_g == rank_aug else 0
                    actual_indicator = self._numeric_scalar(output.value)
                    cross = {
                        "available": True,
                        "independence_class": "DIFFERENT_ENGINE",
                        "engine": "numpy.linalg.matrix_rank",
                        "version": np.__version__,
                        "operation": rule,
                        "passed": actual_indicator is not None and bool(np.isclose(actual_indicator, expected_indicator, atol=1e-10, rtol=0)),
                        "expected_indicator": expected_indicator,
                        "actual_indicator": actual_indicator,
                    }
                else:
                    cross = {"available": False, "independence_class": "NOT_AVAILABLE", "reason": "Span cross-check requires numeric inputs."}
            elif rule == "vector_linear_independence":
                numeric_g = self._numeric_array(parsed_inputs[0])
                if numeric_g is not None:
                    rank_g = np.linalg.matrix_rank(numeric_g)
                    expected_indicator = 1 if rank_g == numeric_g.shape[1] else 0
                    actual_indicator = self._numeric_scalar(output.value)
                    cross = {
                        "available": True,
                        "independence_class": "DIFFERENT_ENGINE",
                        "engine": "numpy.linalg.matrix_rank",
                        "version": np.__version__,
                        "operation": rule,
                        "passed": actual_indicator is not None and bool(np.isclose(actual_indicator, expected_indicator, atol=1e-10, rtol=0)),
                        "expected_indicator": expected_indicator,
                        "actual_indicator": actual_indicator,
                    }
                else:
                    cross = {"available": False, "independence_class": "NOT_AVAILABLE", "reason": "Independence cross-check requires numeric input."}
            elif rule == "vector_basis_of_span":
                numeric_g = self._numeric_array(parsed_inputs[0])
                numeric_b = self._numeric_array(parsed_inputs[1])
                if numeric_g is not None and numeric_b is not None:
                    rank_g = np.linalg.matrix_rank(numeric_g)
                    rank_b = np.linalg.matrix_rank(numeric_b)
                    rank_combined = np.linalg.matrix_rank(np.column_stack([numeric_g, numeric_b]))
                    expected_indicator = 1 if rank_b == rank_g == rank_combined else 0
                    actual_indicator = self._numeric_scalar(output.value)
                    cross = {
                        "available": True,
                        "independence_class": "DIFFERENT_ENGINE",
                        "engine": "numpy.linalg.matrix_rank",
                        "version": np.__version__,
                        "operation": rule,
                        "passed": actual_indicator is not None and bool(np.isclose(actual_indicator, expected_indicator, atol=1e-10, rtol=0)),
                        "expected_indicator": expected_indicator,
                        "actual_indicator": actual_indicator,
                    }
                else:
                    cross = {"available": False, "independence_class": "NOT_AVAILABLE", "reason": "Basis cross-check requires numeric inputs."}
            elif rule == "vector_change_of_basis":
                cross = self._numpy_subspace_compare(rule, parsed_inputs, parsed_outputs)
            elif rule == "matrix_svd":
                numeric_input = self._numeric_array(parsed_inputs[0])
                numeric_outputs = [self._numeric_array(value) for value in parsed_outputs]
                if numeric_input is not None and all(value is not None for value in numeric_outputs):
                    try:
                        _, s_np, _ = np.linalg.svd(numeric_input, full_matrices=False)
                        Uc, Sc, Vhc = [np.asarray(value) for value in numeric_outputs]
                        singular_error = float(np.max(np.abs(np.diag(Sc) - s_np)))
                        reconstruction_error = float(np.max(np.abs(numeric_input - Uc @ Sc @ Vhc)))
                        u_error = float(np.max(np.abs(Uc.conj().T @ Uc - np.eye(Uc.shape[1]))))
                        vh_error = float(np.max(np.abs(Vhc @ Vhc.conj().T - np.eye(Vhc.shape[0]))))
                        scale = max(1.0, float(np.max(np.abs(numeric_input))))
                        tolerance = 1e-9 + 1e-8 * scale
                        passed = singular_error <= tolerance and reconstruction_error <= tolerance and u_error <= tolerance and vh_error <= tolerance and np.all(np.diff(s_np) <= 1e-12)
                        cross = {"available": True, "independence_class": "DIFFERENT_ENGINE", "engine": "numpy.linalg.svd", "version": np.__version__, "operation": rule, "passed": bool(passed), "singular_value_max_abs_error": singular_error, "reconstruction_max_abs_error": reconstruction_error, "U_H_U_max_abs_error": u_error, "Vh_Vh_H_max_abs_error": vh_error, "tolerance": tolerance}
                    except (TypeError, ValueError, np.linalg.LinAlgError):
                        cross = {"available": False, "independence_class": "NOT_AVAILABLE", "reason": "NumPy SVD cross-check failed to execute."}
                else:
                    cross = {"available": False, "independence_class": "NOT_AVAILABLE", "reason": "SVD cross-check requires numeric input and all three numeric outputs."}
            elif rule == "matrix_diagonalize":
                cross = self._numpy_diagonalization_compare(parsed_inputs[0], parsed_outputs[0], parsed_outputs[1])
            elif rule == "vector_gram_schmidt":
                numeric_inputs = [self._numeric_array(x) for x in parsed_inputs]
                if all(x is not None for x in numeric_inputs):
                    reference = []
                    orthonormal = edge.parameters.get("orthonormal", False)
                    for vector in numeric_inputs:
                        q = np.asarray(vector, dtype=complex).reshape(-1).copy()
                        for prior in reference:
                            q = q - (np.vdot(prior, q) / np.vdot(prior, prior)) * prior
                        if orthonormal:
                            q = q / np.linalg.norm(q)
                        reference.append(q)
                    candidate = [self._numeric_array(x).reshape(-1) for x in parsed_outputs]
                    passed = (
                        len(candidate) == len(reference)
                        and all(
                            np.allclose(
                                actual_vector,
                                reference_vector,
                                rtol=1e-8,
                                atol=1e-10,
                                equal_nan=False,
                            )
                            for actual_vector, reference_vector in zip(candidate, reference)
                        )
                    )
                    max_abs_error = max(
                        (
                            float(np.max(np.abs(actual_vector - reference_vector)))
                            for actual_vector, reference_vector in zip(candidate, reference)
                        ),
                        default=0.0,
                    )
                    cross = {
                        "available": True,
                        "independence_class": "DIFFERENT_ENGINE",
                        "engine": "numpy.modified_gram_schmidt",
                        "version": np.__version__,
                        "operation": rule,
                        "passed": bool(passed),
                        "max_abs_error": max_abs_error,
                        "rtol": 1e-8,
                        "atol": 1e-10,
                    }
                else:
                    cross = {
                        "available": False,
                        "independence_class": "NOT_AVAILABLE",
                        "reason": "Gram-Schmidt cross-check requires numeric input vectors.",
                    }
            else:
                cross = {"available": False, "independence_class": "NOT_AVAILABLE",
                         "reason": "Inputs are symbolic or no independent numerical algorithm is configured."}
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
