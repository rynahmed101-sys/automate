"""Verification backend for the Phase 1A Linear Algebra Core."""

from __future__ import annotations

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
        actual_np = cls._numeric_array(actual)
        if actual_np is None:
            return {"available": False, "independence_class": "NOT_AVAILABLE",
                    "reason": "Candidate contains symbolic or non-numeric entries."}
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
            output = parse_linear_algebra_expression(outputs[0].expression.raw_str)
        except LinearAlgebraParseError as exc:
            details["parse_error"] = str(exc)
            return self._failure(edge, graph, start, details, f"Malformed linear-algebra expression: {exc}")

        try:
            numpy_expected = None
            steps = []

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
                a, b = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if a.shape != b.shape:
                    raise ValueError(f"Vector shape mismatch: {a.shape} cannot be dotted with {b.shape}.")
                expected = ParsedLinearAlgebra("scalar", a.dot(b))
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = np.dot(na.reshape(-1), nb.reshape(-1))
                steps.append({"step": 1, "operation": "dot_product", "length": int(a.rows)})

            elif rule == "matrix_multiply":
                if len(parsed_inputs) != 2 or any(x.kind != "matrix" for x in parsed_inputs) or output.kind != "matrix":
                    raise LinearAlgebraParseError("Matrix multiplication requires two matrices and one matrix output.")
                a, b = sp.Matrix(parsed_inputs[0].value), sp.Matrix(parsed_inputs[1].value)
                if a.cols != b.rows:
                    raise ValueError(f"Matrix shape mismatch: {a.shape} cannot multiply {b.shape}.")
                expected = ParsedLinearAlgebra("matrix", a * b)
                na, nb = self._numeric_array(parsed_inputs[0]), self._numeric_array(parsed_inputs[1])
                if na is not None and nb is not None:
                    numpy_expected = na @ nb
                steps.append({"step": 1, "operation": "matrix_multiply", "lhs_shape": list(a.shape),
                              "rhs_shape": list(b.shape), "result_shape": [int(a.rows), int(b.cols)]})

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
                     "rref": [[str(augmented_rref[i, j]) for j in range(augmented_rref.cols)]
                              for i in range(augmented_rref.rows)]},
                    {"step": 3, "operation": "back_substitution", "solution": [str(v) for v in solution]},
                ]
            else:
                raise AssertionError(f"Unhandled linear algebra rule {rule}")

            details["input_shapes"] = [list(x.shape) for x in parsed_inputs]
            details["output_shape"] = list(output.shape)
            details["expected"] = self._display(expected)
            details["actual"] = self._display(output)
            symbolic_passed = self._equal(output, expected)
            details["symbolic_equivalence"] = symbolic_passed
            cross = {"available": False, "independence_class": "NOT_AVAILABLE",
                     "reason": "Inputs are symbolic or no independent numeric algorithm is configured."}
            if numpy_expected is not None:
                cross = self._numpy_compare(output, numpy_expected, rule)
                if not cross["passed"]:
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
