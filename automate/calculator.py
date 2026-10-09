"""Unified machine-friendly mathematical calculator capability layer."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import sympy as sp
import pint
import numpy as np

from automate.ir.safe_parser import SafeParser

_UNIT_REGISTRY = pint.UnitRegistry()

CALCULATOR_OPERATIONS = (
    "evaluate", "simplify", "expand", "factor", "cancel", "apart", "together",
    "collect", "substitute", "differentiate", "integrate", "integrate_definite",
    "limit", "series", "solve", "solve_system", "ode_solve", "pde_solve", "transform", "summation", "product", "roots",
    "nsolve", "evalf", "unit_convert", "descriptive_statistics", "distribution",
    "gradient", "jacobian", "hessian", "total_differential", "divergence", "curl",
    "laplacian", "stationary_points", "matrix_add",
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
        normalized = name.strip()
        if not normalized.isidentifier():
            raise CalculatorError("variable must be a valid symbol name.")
        return sp.Symbol(normalized)
    free = sorted(getattr(expr, "free_symbols", set()), key=lambda s: s.name)
    if len(free) == 1:
        return free[0]
    raise CalculatorError("Provide a variable when the operation needs exactly one variable.")


def _symbols_from_variables(operation: str, variables: list[str] | None) -> list[sp.Symbol]:
    if not variables:
        raise CalculatorError(f"{operation} requires variables, e.g. ['x', 'y'].")
    names = []
    for value in variables:
        if not isinstance(value, str) or not value.strip().isidentifier():
            raise CalculatorError(f"{operation} variables must be valid symbol names.")
        names.append(value.strip())
    if len(set(names)) != len(names):
        raise CalculatorError(f"{operation} variables must be unique.")
    return [sp.Symbol(name) for name in names]


def calculate(
    operation: str,
    expression: Any,
    *,
    variable: str | None = None,
    variables: list[str] | None = None,
    point: Any = None,
    order: int = 6,
    derivative_order: int = 1,
    value: Any = None,
    second_expression: Any = None,
    lower: Any = None,
    upper: Any = None,
    direction: str = "+-",
    equations: list[Any] | None = None,
    dependent_variable: str | None = None,
    independent_variable: str | None = None,
    hint: str = "default",
    transform_type: str | None = None,
    transform_variable: str | None = None,
    inverse: bool = False,
    source_unit: str | None = None,
    target_unit: str | None = None,
    distribution_name: str | None = None,
    distribution_function: str | None = None,
    distribution_parameters: Mapping[str, Any] | None = None,
) -> Any:
    """Run a reusable symbolic operation, retaining native SymPy inputs."""
    if operation not in CALCULATOR_OPERATIONS:
        raise CalculatorError(f"Unsupported operation: {operation}")
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise CalculatorError("order must be a positive integer.")
    if not isinstance(derivative_order, int) or isinstance(derivative_order, bool) or derivative_order < 1:
        raise CalculatorError("derivative_order must be a positive integer.")

    parser = SafeParser()
    if operation == "descriptive_statistics" and isinstance(expression, (list, tuple, np.ndarray)):
        expr = expression
    else:
        expr = (
            _parse_equation(parser, expression)
            if operation in {"solve", "solve_system", "ode_solve", "pde_solve"} else _parse(parser, expression)
        )
    symbol = lambda: _symbol(variable, expr)

    if operation == "evaluate":
        return expr
    if operation == "unit_convert":
        if not isinstance(source_unit, str) or not source_unit.strip():
            raise CalculatorError("unit_convert requires a non-empty source_unit.")
        if not isinstance(target_unit, str) or not target_unit.strip():
            raise CalculatorError("unit_convert requires a non-empty target_unit.")
        if not isinstance(expr, sp.Expr) or expr.is_number is not True or expr.is_real is not True:
            raise CalculatorError("unit_convert requires a real numeric expression without free symbols.")
        if expr.is_finite is False:
            raise CalculatorError("unit_convert requires a finite numeric expression.")
        try:
            quantity = _UNIT_REGISTRY.Quantity(float(expr.evalf()), source_unit.strip())
            return quantity.to(target_unit.strip())
        except (pint.errors.PintError, ValueError, TypeError, OverflowError) as exc:
            raise CalculatorError(f"Could not convert units: {exc}") from exc
    if operation == "descriptive_statistics":
        if isinstance(expr, sp.MatrixBase):
            if expr.rows != 1 and expr.cols != 1:
                raise CalculatorError("descriptive_statistics requires a one-dimensional data sequence.")
            values = list(expr)
        elif isinstance(expr, (list, tuple, np.ndarray)):
            values = list(expr)
        else:
            raise CalculatorError("descriptive_statistics requires a numeric sequence or vector Matrix.")
        if not values:
            raise CalculatorError("descriptive_statistics requires at least one data value.")
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float, np.number, sp.Number))
            or (isinstance(item, sp.Number) and item.is_real is not True)
            for item in values
        ):
            raise CalculatorError("descriptive_statistics accepts only real numeric data values.")
        try:
            samples = np.asarray([float(item) for item in values], dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise CalculatorError(f"Could not convert data to finite numbers: {exc}") from exc
        if not np.isfinite(samples).all():
            raise CalculatorError("descriptive_statistics requires finite data values.")
        return {
            "count": int(samples.size),
            "mean": float(np.mean(samples)),
            "median": float(np.median(samples)),
            "minimum": float(np.min(samples)),
            "maximum": float(np.max(samples)),
            "population_variance": float(np.var(samples, ddof=0)),
            "sample_variance": float(np.var(samples, ddof=1)) if samples.size > 1 else None,
        }
    if operation == "distribution":
        supported_distributions = {"normal", "norm", "uniform", "exponential", "expon", "poisson", "binomial", "binom"}
        if not isinstance(distribution_name, str) or distribution_name not in supported_distributions:
            raise CalculatorError("distribution_name must be normal, uniform, exponential, poisson, or binomial.")
        if not isinstance(distribution_function, str) or distribution_function not in {"pdf", "pmf", "cdf", "sf", "ppf"}:
            raise CalculatorError("distribution_function must be pdf, pmf, cdf, sf, or ppf.")
        if not isinstance(expr, sp.Expr) or expr.is_number is not True or expr.is_real is not True or expr.is_finite is False:
            raise CalculatorError("distribution requires a finite real numeric expression as its evaluation point.")
        if distribution_parameters is not None and not isinstance(distribution_parameters, Mapping):
            raise CalculatorError("distribution_parameters must be a mapping of numeric parameters.")
        parameters = dict(distribution_parameters or {})
        for name, value in parameters.items():
            if not isinstance(name, str) or isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
                raise CalculatorError("Distribution parameters must be finite real numeric values.")
            try:
                finite_value = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise CalculatorError("Distribution parameters must be finite real numeric values.") from exc
            if not np.isfinite(finite_value):
                raise CalculatorError("Distribution parameters must be finite real numeric values.")
        point = float(expr.evalf())
        if distribution_function == "ppf" and not 0 <= point <= 1:
            raise CalculatorError("ppf requires an evaluation point in the probability interval [0, 1].")
        from scipy import stats as scipy_stats

        distributions = {
            "normal": scipy_stats.norm,
            "norm": scipy_stats.norm,
            "uniform": scipy_stats.uniform,
            "exponential": scipy_stats.expon,
            "expon": scipy_stats.expon,
            "poisson": scipy_stats.poisson,
            "binomial": scipy_stats.binom,
            "binom": scipy_stats.binom,
        }
        distribution = distributions[distribution_name]
        method = getattr(distribution, distribution_function, None)
        if method is None:
            raise CalculatorError(
                f"Distribution '{distribution_name}' does not support {distribution_function}."
            )
        try:
            result = float(method(point, **parameters))
        except (TypeError, ValueError, OverflowError) as exc:
            raise CalculatorError(f"Could not evaluate distribution: {exc}") from exc
        if not np.isfinite(result):
            raise CalculatorError("Distribution evaluation returned a non-finite result; check its parameters and domain.")
        return result
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
        return sp.diff(expr, symbol(), derivative_order)
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
        symbols = _symbols_from_variables(operation, variables)
        if equations is not None:
            if not isinstance(equations, (list, tuple)) or not equations:
                raise CalculatorError("equations must be a non-empty list of equations.")
            system = [_parse_equation(parser, item) for item in equations]
        else:
            if second_expression is None:
                raise CalculatorError("solve_system requires second_expression or equations.")
            system = [expr, _parse_equation(parser, second_expression)]
        return sp.solve(system, symbols)
    if operation == "transform":
        if transform_type not in {"laplace", "fourier"}:
            raise CalculatorError("transform_type must be 'laplace' or 'fourier'.")
        if not isinstance(transform_variable, str) or not transform_variable.isidentifier():
            raise CalculatorError("transform requires transform_variable as a valid symbol name.")
        if not isinstance(inverse, bool):
            raise CalculatorError("inverse must be a boolean.")
        source = _symbol(variable, expr)
        target = sp.Symbol(transform_variable)
        if transform_type == "laplace":
            return (
                sp.inverse_laplace_transform(expr, source, target)
                if inverse else sp.laplace_transform(expr, source, target, noconds=True)
            )
        return (
            sp.inverse_fourier_transform(expr, source, target)
            if inverse else sp.fourier_transform(expr, source, target)
        )
    if operation == "pde_solve":
        try:
            return sp.pdsolve(expr)
        except (ValueError, NotImplementedError, TypeError) as exc:
            raise CalculatorError(f"Could not solve the requested PDE: {type(exc).__name__}: {exc}") from exc
    if operation == "ode_solve":
        if not isinstance(dependent_variable, str) or not dependent_variable.isidentifier():
            raise CalculatorError("ode_solve requires dependent_variable as a valid function name, e.g. 'y'.")
        if not isinstance(independent_variable, str) or not independent_variable.isidentifier():
            raise CalculatorError("ode_solve requires independent_variable as a valid symbol name, e.g. 'x'.")
        if not isinstance(hint, str) or not hint.strip():
            raise CalculatorError("hint must be a non-empty SymPy dsolve hint name.")
        independent = sp.Symbol(independent_variable)
        function = sp.Function(dependent_variable)(independent)
        try:
            return sp.dsolve(expr, function, hint=hint)
        except (ValueError, NotImplementedError, TypeError) as exc:
            raise CalculatorError(f"Could not solve the requested ODE: {type(exc).__name__}: {exc}") from exc
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
    if operation == "stationary_points":
        symbols = _symbols_from_variables(operation, variables)
        gradient = [sp.diff(expr, name) for name in symbols]
        if all(sp.simplify(component) == 0 for component in gradient):
            raise CalculatorError(
                "The expression is independent of all requested variables; "
                "the stationary set is not a finite list of points."
            )
        points = sp.solve(gradient, symbols, dict=True)
        if any(any(name not in point for name in symbols) for point in points):
            raise CalculatorError(
                "The stationary set has free requested variables and is not a finite list of points."
            )
        return points
    if operation in {
        "gradient", "jacobian", "hessian", "total_differential",
        "divergence", "curl", "laplacian",
    }:
        vs = _symbols_from_variables(operation, variables)
        if operation == "gradient":
            return sp.Matrix([sp.diff(expr, v) for v in vs])
        if operation == "hessian":
            return sp.hessian(expr, vs)
        if operation == "total_differential":
            if not isinstance(expr, sp.Expr):
                raise CalculatorError("total_differential requires a scalar expression.")
            differential_names = {f"d_{variable.name}" for variable in vs}
            expression_names = {symbol.name for symbol in expr.free_symbols}
            variable_names = {variable.name for variable in vs}
            if differential_names & (expression_names | variable_names):
                raise CalculatorError(
                    "total_differential generated differential symbols must not collide "
                    "with expression or variable symbols."
                )
            return sp.Add(*(
                sp.diff(expr, variable) * sp.Symbol(f"d_{variable}")
                for variable in vs
            ))
        if operation == "laplacian":
            if not isinstance(expr, sp.Expr):
                raise CalculatorError("laplacian requires a scalar expression.")
            return sp.Add(*(sp.diff(expr, variable, 2) for variable in vs))
        if operation in {"divergence", "curl"}:
            if not isinstance(expr, sp.MatrixBase) or (expr.rows != 1 and expr.cols != 1):
                raise CalculatorError(f"{operation} requires a row or column Matrix vector field.")
            components = list(expr)
            if len(components) != len(vs):
                raise CalculatorError(f"{operation} requires one variable per vector component.")
            if operation == "divergence":
                return sp.Add(*(sp.diff(component, variable) for component, variable in zip(components, vs)))
            if len(vs) != 3:
                raise CalculatorError("curl is defined here only for three-dimensional vector fields.")
            x, y, z = vs
            fx, fy, fz = components
            return sp.Matrix([
                sp.diff(fz, y) - sp.diff(fy, z),
                sp.diff(fx, z) - sp.diff(fz, x),
                sp.diff(fy, x) - sp.diff(fx, y),
            ])
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
    if isinstance(result, pint.Quantity):
        return f"{sp.sstr(result.magnitude)} {result.units}"
    return sp.sstr(result)


_OPERATION_ARGUMENTS = {
    "collect": (("expression",), ("variable",)),
    "evalf": (("expression",), ("order",)),
    "substitute": (("expression", "value"), ()),
    "differentiate": (("expression",), ("variable", "derivative_order")),
    "integrate": (("expression",), ("variable",)),
    "integrate_definite": (("expression", "lower", "upper"), ("variable",)),
    "limit": (("expression", "point"), ("variable", "direction")),
    "series": (("expression",), ("variable", "point", "order")),
    "solve": (("expression",), ("variable",)),
    "solve_system": (("expression", "variables"), ("second_expression", "equations")),
    "ode_solve": (("expression", "dependent_variable", "independent_variable"), ("hint",)),
    "pde_solve": (("expression",), ()),
    "unit_convert": (("expression", "source_unit", "target_unit"), ()),
    "descriptive_statistics": (("expression",), ()),
    "distribution": (("expression", "distribution_name", "distribution_function"), ("distribution_parameters",)),
    "transform": (("expression", "transform_type", "transform_variable"), ("variable", "inverse")),
    "summation": (("expression", "point"), ("variable",)),
    "product": (("expression", "point"), ("variable",)),
    "roots": (("expression",), ("variable",)),
    "nsolve": (("expression", "value"), ("variable",)),
    "gradient": (("expression", "variables"), ()),
    "jacobian": (("expression", "variables"), ()),
    "hessian": (("expression", "variables"), ()),
    "total_differential": (("expression", "variables"), ()),
    "divergence": (("expression", "variables"), ()),
    "curl": (("expression", "variables"), ()),
    "laplacian": (("expression", "variables"), ()),
    "stationary_points": (("expression", "variables"), ()),
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
    "differentiate": "Compute a symbolic derivative; derivative_order selects the derivative order (1 by default).",
    "integrate": "Compute a symbolic indefinite integral.",
    "integrate_definite": "Compute a definite integral between lower and upper bounds.",
    "limit": "Compute a symbolic limit at point; direction may be '+', '-', or '+-'.",
    "series": (
        "Expand around point (zero by default) using SymPy's order convention: "
        "include powers below order and retain the Order term."
    ),
    "solve": "Solve an expression or equation for a variable.",
    "solve_system": "Solve a system using second_expression or an equations list.",
    "ode_solve": "Solve an ordinary differential equation with SymPy dsolve; name the dependent and independent variables.",
    "pde_solve": "Attempt symbolic partial differential equation solving through SymPy pdsolve.",
    "unit_convert": "Convert a finite real numeric magnitude between compatible units using Pint; the magnitude is returned as an approximate float quantity.",
    "descriptive_statistics": "Compute count, mean, median, extrema, population variance, and sample variance for a finite real numeric sequence.",
    "distribution": "Numerically evaluate the pdf, pmf, cdf, survival function, or quantile of an allowlisted common SciPy distribution.",
    "transform": "Compute a symbolic Laplace or Fourier transform; set inverse=true for the inverse transform.",
    "summation": "Compute a finite symbolic sum over point='start,end'.",
    "product": "Compute a finite symbolic product over point='start,end'.",
    "roots": "Return polynomial roots and multiplicities.",
    "nsolve": "Numerically solve an equation from an initial guess.",
    "evalf": "Evaluate a mathematical object to the requested precision.",
    "gradient": "Compute the vector of first partial derivatives.",
    "jacobian": "Compute a Jacobian matrix.",
    "hessian": "Compute a Hessian matrix.",
    "total_differential": "Compute the total differential as a linear form in d_<variable> symbols.",
    "divergence": "Compute the Cartesian divergence of a vector field with one component per variable.",
    "curl": "Compute the three-dimensional Cartesian curl of a vector field.",
    "laplacian": "Compute the scalar Cartesian Laplacian across the requested variables.",
    "stationary_points": "Find symbolic candidates where every requested first partial derivative is zero; this does not classify minima or maxima.",
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
    "operation", "expression", "variable", "variables", "point", "order", "derivative_order",
    "value", "second_expression", "lower", "upper", "direction", "equations",
    "dependent_variable", "independent_variable", "hint", "transform_type", "transform_variable", "inverse",
    "source_unit", "target_unit",
    "distribution_name", "distribution_function", "distribution_parameters",
}


def calculator_manifest() -> dict[str, Any]:
    """Return a stable, machine-readable description of the callable calculator API."""
    operations = []
    for name in CALCULATOR_OPERATIONS:
        required, optional = _OPERATION_ARGUMENTS.get(name, (("expression",), ()))
        operation = {
            "name": name,
            "description": _OPERATION_DESCRIPTIONS.get(name, f"Apply the {name} operation."),
            "required": list(required),
            "optional": list(optional),
            "input_forms": ["expression_string", "SymPy_object"],
        }
        if name == "unit_convert":
            operation.update({
                "input_forms": ["numeric_expression_string", "SymPy_number"],
                "arguments": {
                    "expression": {"type": "finite_real_number"},
                    "source_unit": {"type": "unit_string"},
                    "target_unit": {"type": "compatible_unit_string"},
                },
                "result": {"type": "quantity", "magnitude": "approximate_float", "units": "converted_target_unit"},
            })
        elif name == "descriptive_statistics":
            operation.update({
                "input_forms": ["numeric_sequence", "NumPy_vector", "SymPy_vector", "SafeParser_Matrix_expression"],
                "arguments": {"expression": {"type": "one_dimensional_finite_real_numeric_data"}},
                "result": {
                    "type": "mapping",
                    "keys": ["count", "mean", "median", "minimum", "maximum", "population_variance", "sample_variance"],
                    "sample_variance": "null when fewer than two values are provided",
                },
            })
        elif name == "distribution":
            operation.update({
                "input_forms": ["numeric_expression_string", "SymPy_number"],
                "arguments": {
                    "expression": {"type": "finite_real_evaluation_point"},
                    "distribution_name": {"type": "string", "choices": ["normal", "norm", "uniform", "exponential", "expon", "poisson", "binomial", "binom"]},
                    "distribution_function": {"type": "string", "choices": ["pdf", "pmf", "cdf", "sf", "ppf"]},
                    "functions_by_distribution": {
                        "normal": ["pdf", "cdf", "sf", "ppf"],
                        "norm": ["pdf", "cdf", "sf", "ppf"],
                        "uniform": ["pdf", "cdf", "sf", "ppf"],
                        "exponential": ["pdf", "cdf", "sf", "ppf"],
                        "expon": ["pdf", "cdf", "sf", "ppf"],
                        "poisson": ["pmf", "cdf", "sf", "ppf"],
                        "binomial": ["pmf", "cdf", "sf", "ppf"],
                        "binom": ["pmf", "cdf", "sf", "ppf"],
                    },
                    "distribution_parameters": {"type": "mapping_of_finite_real_numbers"},
                },
                "result": {"type": "float", "approximate": True},
            })
        operations.append(operation)
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
    if isinstance(result, pint.Quantity):
        return {
            "type": "quantity",
            "magnitude": result_data(result.magnitude),
            "units": str(result.units),
            "approximate": True,
        }
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
    if isinstance(result, Mapping):
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
