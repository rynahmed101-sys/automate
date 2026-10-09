"""Unified machine-friendly mathematical calculator capability layer."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import sympy as sp

from automate.ir.safe_parser import SafeParser

CALCULATOR_OPERATIONS = (
    "evaluate", "simplify", "expand", "factor", "cancel", "apart", "together",
    "collect", "substitute", "differentiate", "integrate", "integrate_definite",
    "limit", "series", "solve", "solve_system", "summation", "product", "roots",
    "nsolve", "evalf", "gradient", "jacobian", "hessian", "matrix_add",
    "matrix_multiply", "matrix_transpose", "matrix_determinant", "matrix_inverse",
    "matrix_rank", "matrix_trace", "matrix_eigenvalues", "matrix_eigenvectors",
    "matrix_singular_values", "vector_dot", "vector_cross", "vector_norm",
)


class CalculatorError(ValueError):
    """A calculation request could not be completed."""


def _parse(parser: SafeParser, value: Any) -> Any:
    if isinstance(value, (sp.Basic, sp.MatrixBase)):
        return value
    if not isinstance(value, str):
        raise CalculatorError(
            f"Expression must be a string or SymPy mathematical object, got {type(value).__name__}."
        )
    return parser.parse_isolated(value)


def _parse_equation(parser: SafeParser, value: Any) -> Any:
    if isinstance(value, sp.Equality):
        return value
    if isinstance(value, str) and "=" in value:
        return parser.parse_equation_isolated(value)
    return _parse(parser, value)


def _symbol(name: str | None, expr: Any) -> sp.Symbol:
    if name:
        return sp.Symbol(name)
    free = sorted(getattr(expr, "free_symbols", set()), key=lambda s: s.name)
    if len(free) == 1:
        return free[0]
    raise CalculatorError("Provide a variable when the operation needs exactly one variable.")


def calculate(
    operation: str,
    expression: Any,
    *,
    variable: str | None = None,
    variables: list[str] | None = None,
    point: Any = None,
    order: int = 6,
    value: Any = None,
    second_expression: Any = None,
    lower: Any = None,
    upper: Any = None,
    direction: str = "+-",
    equations: list[Any] | None = None,
) -> Any:
    """Run a reusable symbolic operation, retaining native SymPy inputs."""
    if operation not in CALCULATOR_OPERATIONS:
        raise CalculatorError(f"Unsupported operation: {operation}")
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise CalculatorError("order must be a positive integer.")

    parser = SafeParser()
    expr = (
        _parse_equation(parser, expression)
        if operation in {"solve", "solve_system"} else _parse(parser, expression)
    )
    symbol = lambda: _symbol(variable, expr)

    if operation == "evaluate":
        return expr
    if operation == "simplify":
        return sp.simplify(expr)
    if operation == "expand":
        return sp.expand(expr)
    if operation == "factor":
        return sp.factor(expr)
    if operation == "cancel":
        return sp.cancel(expr)
    if operation == "apart":
        return sp.apart(expr)
    if operation == "together":
        return sp.together(expr)
    if operation == "collect":
        return sp.collect(expr, symbol())
    if operation == "substitute":
        if not isinstance(value, str) or "=" not in value:
            raise CalculatorError("substitute requires value='NAME=EXPRESSION'.")
        name, replacement = value.split("=", 1)
        name = name.strip()
        if not name.isidentifier():
            raise CalculatorError("Substitution target must be a valid symbol name.")
        return expr.subs(sp.Symbol(name), _parse(parser, replacement))
    if operation == "differentiate":
        return sp.diff(expr, symbol(), order)
    if operation == "integrate":
        return sp.integrate(expr, symbol())
    if operation == "integrate_definite":
        if lower is None or upper is None:
            raise CalculatorError("integrate_definite requires both lower and upper bounds.")
        return sp.integrate(expr, (symbol(), _parse(parser, lower), _parse(parser, upper)))
    if operation == "limit":
        if point is None:
            raise CalculatorError("limit requires point.")
        if direction not in {"+", "-", "+-"}:
            raise CalculatorError("direction must be '+', '-', or '+-'.")
        return sp.limit(expr, symbol(), _parse(parser, point), dir=direction)
    if operation == "series":
        expansion_point = sp.S.Zero if point is None else _parse(parser, point)
        return sp.series(expr, symbol(), expansion_point, order)
    if operation == "solve":
        return sp.solve(expr, symbol())
    if operation == "solve_system":
        if not variables:
            raise CalculatorError("solve_system requires variables, e.g. ['x', 'y'].")
        symbols = [sp.Symbol(v.strip()) for v in variables if isinstance(v, str) and v.strip()]
        if len(symbols) != len(variables):
            raise CalculatorError("Every solve_system variable must be a non-empty string.")
        if equations is not None:
            if not isinstance(equations, (list, tuple)) or not equations:
                raise CalculatorError("equations must be a non-empty list of equations.")
            system = [_parse_equation(parser, item) for item in equations]
        else:
            if second_expression is None:
                raise CalculatorError("solve_system requires second_expression or equations.")
            system = [expr, _parse_equation(parser, second_expression)]
        return sp.solve(system, symbols, dict=True)
    if operation in {"summation", "product"}:
        if point is None or not isinstance(point, str) or "," not in point:
            raise CalculatorError(f"{operation} requires point='START,END'.")
        start, end = map(str.strip, point.split(",", 1))
        return getattr(sp, operation)(expr, (symbol(), _parse(parser, start), _parse(parser, end)))
    if operation == "roots":
        return sp.roots(expr, symbol())
    if operation == "nsolve":
        if value is None:
            raise CalculatorError("nsolve requires value (an initial guess).")
        return sp.nsolve(expr, symbol(), _parse(parser, value))
    if operation == "evalf":
        return expr.evalf(order)
    if operation in {"gradient", "jacobian", "hessian"}:
        vs = [sp.Symbol(v.strip()) for v in (variables or []) if isinstance(v, str) and v.strip()]
        if not vs:
            raise CalculatorError(f"{operation} requires variables, e.g. ['x', 'y'].")
        if operation == "gradient":
            return sp.Matrix([sp.diff(expr, v) for v in vs])
        if operation == "hessian":
            return sp.hessian(expr, vs)
        funcs = list(expr) if isinstance(expr, sp.MatrixBase) else [expr]
        return sp.Matrix(funcs).jacobian(vs)
    if operation.startswith("matrix_") or operation.startswith("vector_"):
        if not isinstance(expr, sp.MatrixBase):
            raise CalculatorError("This operation requires a Matrix expression.")
        if operation in {"matrix_add", "matrix_multiply", "vector_dot", "vector_cross"}:
            if second_expression is None:
                raise CalculatorError(f"{operation} requires second_expression.")
            other = _parse(parser, second_expression)
            if operation in {"matrix_add", "matrix_multiply"} and not isinstance(other, sp.MatrixBase):
                raise CalculatorError(f"{operation} requires a second Matrix expression.")
            if operation == "matrix_add":
                return expr + other
            if operation == "matrix_multiply":
                return expr * other
            if not isinstance(other, sp.MatrixBase):
                raise CalculatorError(f"{operation} requires a second Matrix expression.")
            return expr.dot(other) if operation == "vector_dot" else expr.cross(other)
        if operation == "matrix_transpose":
            return expr.T
        if operation == "matrix_determinant":
            return expr.det()
        if operation == "matrix_inverse":
            return expr.inv()
        if operation == "matrix_rank":
            return expr.rank()
        if operation == "matrix_trace":
            return expr.trace()
        if operation == "matrix_eigenvalues":
            return expr.eigenvals()
        if operation == "matrix_eigenvectors":
            return expr.eigenvects()
        if operation == "matrix_singular_values":
            return expr.singular_values()
        if operation == "vector_norm":
            return sp.sqrt(expr.dot(expr))
    raise CalculatorError(f"Operation '{operation}' is not implemented.")


def result_string(result: Any) -> str:
    return sp.sstr(result)


_OPERATION_ARGUMENTS = {
    "collect": (("expression",), ("variable",)),
    "evalf": (("expression",), ("order",)),
    "substitute": (("expression", "value"), ()),
    "differentiate": (("expression",), ("variable", "order")),
    "integrate": (("expression",), ("variable",)),
    "integrate_definite": (("expression", "lower", "upper"), ("variable",)),
    "limit": (("expression", "point"), ("variable", "direction")),
    "series": (("expression",), ("variable", "point", "order")),
    "solve": (("expression",), ("variable",)),
    "solve_system": (("expression", "variables"), ("second_expression", "equations")),
    "summation": (("expression", "point"), ("variable",)),
    "product": (("expression", "point"), ("variable",)),
    "roots": (("expression",), ("variable",)),
    "nsolve": (("expression", "value"), ("variable",)),
    "gradient": (("expression", "variables"), ()),
    "jacobian": (("expression", "variables"), ()),
    "hessian": (("expression", "variables"), ()),
    "matrix_add": (("expression", "second_expression"), ()),
    "matrix_multiply": (("expression", "second_expression"), ()),
    "vector_dot": (("expression", "second_expression"), ()),
    "vector_cross": (("expression", "second_expression"), ()),
    "matrix_transpose": (("expression",), ()),
    "matrix_determinant": (("expression",), ()),
    "matrix_inverse": (("expression",), ()),
    "matrix_rank": (("expression",), ()),
    "matrix_trace": (("expression",), ()),
    "matrix_eigenvalues": (("expression",), ()),
    "matrix_eigenvectors": (("expression",), ()),
    "matrix_singular_values": (("expression",), ()),
    "vector_norm": (("expression",), ()),
}
_OPERATION_DESCRIPTIONS = {
    "evaluate": "Parse an expression into a mathematical object without forcing numeric evaluation.",
    "simplify": "Apply symbolic simplification.",
    "expand": "Expand products and powers.",
    "factor": "Factor an expression.",
    "cancel": "Cancel common rational factors.",
    "apart": "Decompose a rational function into partial fractions.",
    "together": "Combine rational terms into a common fraction.",
    "collect": "Collect terms by powers of a variable.",
    "substitute": "Substitute one named symbol using value='name=expression'.",
    "differentiate": "Compute a symbolic derivative; order selects the derivative order.",
    "integrate": "Compute a symbolic indefinite integral.",
    "integrate_definite": "Compute a definite integral between lower and upper bounds.",
    "limit": "Compute a symbolic limit at point; direction may be '+', '-', or '+-'.",
    "series": "Expand around point (zero by default) through the requested order.",
    "solve": "Solve an expression or equation for a variable.",
    "solve_system": "Solve a system using second_expression or an equations list.",
    "summation": "Compute a finite symbolic sum over point='start,end'.",
    "product": "Compute a finite symbolic product over point='start,end'.",
    "roots": "Return polynomial roots and multiplicities.",
    "nsolve": "Numerically solve an equation from an initial guess.",
    "evalf": "Evaluate a mathematical object to the requested precision.",
    "gradient": "Compute the vector of first partial derivatives.",
    "jacobian": "Compute a Jacobian matrix.",
    "hessian": "Compute a Hessian matrix.",
    "matrix_add": "Add two matrices.",
    "matrix_multiply": "Multiply two matrices.",
    "matrix_transpose": "Transpose a matrix.",
    "matrix_determinant": "Compute a matrix determinant.",
    "matrix_inverse": "Compute a matrix inverse.",
    "matrix_rank": "Compute matrix rank.",
    "matrix_trace": "Compute matrix trace.",
    "matrix_eigenvalues": "Compute matrix eigenvalues and multiplicities.",
    "matrix_eigenvectors": "Compute matrix eigenvectors and eigenspaces.",
    "matrix_singular_values": "Compute matrix singular values.",
    "vector_dot": "Compute a vector dot product.",
    "vector_cross": "Compute a vector cross product.",
    "vector_norm": "Compute the Euclidean norm from the dot product.",
}
_REQUEST_FIELDS = {
    "operation", "expression", "variable", "variables", "point", "order",
    "value", "second_expression", "lower", "upper", "direction", "equations",
}


def calculator_manifest() -> dict[str, Any]:
    """Return a stable, machine-readable description of the callable calculator API."""
    operations = []
    for name in CALCULATOR_OPERATIONS:
        required, optional = _OPERATION_ARGUMENTS.get(name, (("expression",), ()))
        operations.append({
            "name": name,
            "description": _OPERATION_DESCRIPTIONS.get(name, f"Apply the {name} operation."),
            "required": list(required),
            "optional": list(optional),
            "input_forms": ["expression_string", "SymPy_object"],
        })
    return {
        "schema_version": "automate.calculator.v1",
        "role": "mathematics_and_physics_calculator",
        "interpretation": "external_ai",
        "verification": "optional",
        "request_fields": sorted(_REQUEST_FIELDS),
        "operations": operations,
    }


def calculate_request(request: Any) -> Any:
    """Execute a mapping request, suitable for adapters and tool wrappers."""
    if not isinstance(request, Mapping):
        raise CalculatorError("Request must be a mapping with operation and expression fields.")
    unknown = set(request) - _REQUEST_FIELDS
    if unknown:
        raise CalculatorError("Unknown request field(s): " + ", ".join(sorted(map(str, unknown))))
    if "operation" not in request or "expression" not in request:
        raise CalculatorError("Request requires both 'operation' and 'expression'.")
    kwargs = {
        key: request[key]
        for key in _REQUEST_FIELDS - {"operation", "expression"}
        if key in request
    }
    if "variables" in kwargs and isinstance(kwargs["variables"], str):
        kwargs["variables"] = [part.strip() for part in kwargs["variables"].split(",") if part.strip()]
    if "equations" in kwargs and isinstance(kwargs["equations"], str):
        raise CalculatorError("equations must be a JSON array or Python list of equation expressions.")
    return calculate(request["operation"], request["expression"], **kwargs)


def result_data(result: Any) -> dict[str, Any]:
    """Serialize common calculator results into JSON-safe, type-aware data."""
    if isinstance(result, sp.MatrixBase):
        return {
            "type": "matrix",
            "shape": [int(result.rows), int(result.cols)],
            "entries": [[sp.sstr(result[i, j]) for j in range(result.cols)] for i in range(result.rows)],
            "text": sp.sstr(result),
        }
    if isinstance(result, sp.Basic):
        return {
            "type": "sympy",
            "text": sp.sstr(result),
            "srepr": sp.srepr(result),
            "is_number": bool(result.is_number),
        }
    if isinstance(result, dict):
        return {
            "type": "mapping",
            "items": [
                {
                    "key": result_data(k) if isinstance(k, (sp.Basic, sp.MatrixBase, dict, list, tuple))
                    else {"type": type(k).__name__, "text": str(k)},
                    "value": result_data(v),
                }
                for k, v in result.items()
            ],
        }
    if isinstance(result, (list, tuple, set)):
        return {
            "type": "sequence",
            "sequence_type": type(result).__name__,
            "items": [result_data(item) for item in result],
        }
    if result is None or isinstance(result, (str, int, float, bool)):
        return {"type": "scalar", "python_type": type(result).__name__, "value": result, "text": str(result)}
    return {"type": type(result).__name__, "text": result_string(result)}
