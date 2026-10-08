"""Unified machine-friendly mathematical calculator capability layer."""
from __future__ import annotations
from typing import Any
import sympy as sp
from automate.ir.safe_parser import SafeParser

CALCULATOR_OPERATIONS = (
"evaluate","simplify","expand","factor","cancel","apart","together","collect","substitute",
"differentiate","integrate","limit","series","solve","solve_system","summation",
"product","roots","nsolve","evalf","gradient","jacobian","hessian",
"matrix_add","matrix_multiply","matrix_transpose","matrix_determinant","matrix_inverse",
"matrix_rank","matrix_trace","matrix_eigenvalues","matrix_eigenvectors","matrix_singular_values",
"vector_dot","vector_cross","vector_norm",
)

class CalculatorError(ValueError):
    """A calculation request could not be completed."""

def _parse(parser: SafeParser, value: str) -> Any:
    return parser.parse_isolated(value)

def _symbol(name: str | None, expr: Any) -> sp.Symbol:
    if name: return sp.Symbol(name)
    free = sorted(getattr(expr, "free_symbols", set()), key=lambda s: s.name)
    if len(free) == 1: return free[0]
    raise CalculatorError("Provide --variable when the operation needs exactly one variable.")

def calculate(operation: str, expression: str, *, variable: str | None=None,
              variables: list[str] | None=None, point: str | None=None,
              order: int=6, value: str | None=None,
              second_expression: str | None=None) -> Any:
    if operation not in CALCULATOR_OPERATIONS:
        raise CalculatorError(f"Unsupported operation: {operation}")
    p=SafeParser(); expr=_parse(p,expression)
    s=lambda: _symbol(variable,expr)
    if operation=="evaluate": return expr
    if operation=="simplify": return sp.simplify(expr)
    if operation=="expand": return sp.expand(expr)
    if operation=="factor": return sp.factor(expr)
    if operation=="cancel": return sp.cancel(expr)
    if operation=="apart": return sp.apart(expr)
    if operation=="together": return sp.together(expr)
    if operation=="collect": return sp.collect(expr,s())
    if operation=="substitute":
        if not value or "=" not in value: raise CalculatorError("substitute requires --value NAME=EXPRESSION.")
        name,repl=value.split("=",1); return expr.subs(sp.Symbol(name.strip()),_parse(p,repl))
    if operation=="differentiate": return sp.diff(expr,s())
    if operation=="integrate": return sp.integrate(expr,s())
    if operation=="limit":
        if point is None: raise CalculatorError("limit requires --point.")
        return sp.limit(expr,s(),_parse(p,point))
    if operation=="series": return sp.series(expr,s(),0,order)
    if operation=="solve":
        target = p.parse_equation_isolated(expression) if "=" in expression else expr
        return sp.solve(target, s())
    if operation=="solve_system":
        if not second_expression or not variables: raise CalculatorError("solve_system requires --second-expression and --variables x,y.")
        return sp.solve((expr,_parse(p,second_expression)),[sp.Symbol(v.strip()) for v in variables])
    if operation in {"summation","product"}:
        if point is None or "," not in point: raise CalculatorError(f"{operation} requires --point START,END.")
        a,b=map(str.strip,point.split(",",1)); bounds=(s(),_parse(p,a),_parse(p,b))
        return getattr(sp,operation)(expr,bounds)
    if operation=="roots": return sp.roots(expr, s())
    if operation=="nsolve":
        if value is None: raise CalculatorError("nsolve requires --value INITIAL_GUESS.")
        return sp.nsolve(expr,s(),_parse(p,value))
    if operation=="evalf": return expr.evalf(order)
    if operation in {"gradient","jacobian","hessian"}:
        vs=[sp.Symbol(v.strip()) for v in (variables or [])]
        if not vs: raise CalculatorError(f"{operation} requires --variables x,y,...")
        if operation=="gradient": return sp.Matrix([sp.diff(expr,v) for v in vs])
        if operation=="hessian": return sp.hessian(expr,vs)
        funcs=list(expr) if isinstance(expr,sp.MatrixBase) else [expr]
        return sp.Matrix(funcs).jacobian(vs)
    if operation.startswith("matrix_") or operation.startswith("vector_"):
        if not isinstance(expr,sp.MatrixBase): raise CalculatorError("This operation requires a Matrix expression.")
        if operation in {"matrix_add","matrix_multiply"}:
            if not second_expression: raise CalculatorError(f"{operation} requires --second-expression.")
            other=_parse(p,second_expression)
            return expr+other if operation=="matrix_add" else expr*other
        if operation=="matrix_transpose": return expr.T
        if operation=="matrix_determinant": return expr.det()
        if operation=="matrix_inverse": return expr.inv()
        if operation=="matrix_rank": return expr.rank()
        if operation=="matrix_trace": return expr.trace()
        if operation=="matrix_eigenvalues": return expr.eigenvals()
        if operation=="matrix_eigenvectors": return expr.eigenvects()
        if operation=="matrix_singular_values": return expr.singular_values()
        if operation in {"vector_dot","vector_cross"}:
            if not second_expression: raise CalculatorError(f"{operation} requires --second-expression.")
            other=_parse(p,second_expression)
            return expr.dot(other) if operation=="vector_dot" else expr.cross(other)
        if operation=="vector_norm": return sp.sqrt(expr.dot(expr))
    raise CalculatorError(f"Operation '{operation}' is not implemented.")

def result_string(result: Any) -> str:
    return sp.sstr(result)
