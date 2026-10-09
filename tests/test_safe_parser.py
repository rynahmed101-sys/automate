"""
Adversarial tests for the SafeParser restricted mathematical expression parser.

Every test here attempts a known-bad input category. Every test MUST fail
with SafeParseError. Tests that pass SafeParser undetected are bugs.

Test categories:
  A. Python code injection (import, eval, exec, os, sys, subprocess)
  B. Attribute traversal attacks (__dunder__, getattr)
  C. Arbitrary class/object construction
  D. Filesystem and network access attempts
  E. DoS via expression size / depth
  F. Valid physics expressions (must parse successfully)
  G. Edge cases (empty, type errors, too-long strings)
"""

import pytest
import sympy as sp
from automate.ir.safe_parser import SafeParser, SafeParseError


@pytest.fixture
def parser():
    return SafeParser()


# ---------------------------------------------------------------------------
# A. Python code injection
# ---------------------------------------------------------------------------

class TestCodeInjection:

    def test_import_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("__import__('os')")

    def test_import_keyword_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("import os")

    def test_eval_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("eval('1+1')")

    def test_exec_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("exec('print(1)')")

    def test_lambda_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("lambda x: x + 1")

    def test_semicolon_injection(self, parser):
        """Semicolons separate Python statements — must be blocked."""
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("x + 1; import os")

    def test_walrus_operator_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("(y := x + 1)")

    def test_yield_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("yield x")


# ---------------------------------------------------------------------------
# B. Attribute traversal attacks
# ---------------------------------------------------------------------------

class TestAttributeTraversal:

    def test_dunder_import_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("x.__class__.__bases__[0].__subclasses__()")

    def test_dunder_dict_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("x.__dict__")

    def test_getattr_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("getattr(x, '__class__')")

    def test_dunder_init_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("x.__init__")

    def test_dunder_doc_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("sin.__doc__")

    def test_type_call_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("type(x)")


# ---------------------------------------------------------------------------
# C. Arbitrary class/object construction
# ---------------------------------------------------------------------------

class TestClassConstruction:

    def test_globals_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("globals()")

    def test_locals_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("locals()")

    def test_vars_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("vars()")

    def test_dir_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("dir(x)")

    def test_compile_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("compile('x+1', '', 'eval')")

    def test_builtins_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("__builtins__['eval']('1')")


# ---------------------------------------------------------------------------
# D. Filesystem and network access
# ---------------------------------------------------------------------------

class TestFilesystemNetwork:

    def test_open_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("open('/etc/passwd').read()")

    def test_os_system_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("os.system('ls')")

    def test_os_environ_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("os.environ['HOME']")

    def test_subprocess_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("subprocess.run(['ls'])")

    def test_path_traversal_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("../../etc/passwd")

    def test_socket_blocked(self, parser):
        with pytest.raises(SafeParseError, match="disallowed pattern"):
            parser.parse("socket.connect(('evil.com', 80))")


# ---------------------------------------------------------------------------
# E. DoS via expression size / depth
# ---------------------------------------------------------------------------

class TestDoSPrevention:

    def test_deeply_nested_expression(self, parser):
        """10000 levels of nested sin — must be rejected on depth."""
        depth = 5000
        expr_str = "sin(" * depth + "x" + ")" * depth
        with pytest.raises(SafeParseError):
            parser.parse(expr_str)

    def test_huge_string_rejected(self, parser):
        """String exceeding MAX_STRING_LENGTH must be rejected before parsing."""
        huge = "x + " * 2000 + "x"
        with pytest.raises(SafeParseError):
            parser.parse(huge)

    def test_many_atoms_rejected(self, parser):
        """Expression with too many distinct symbols must be rejected."""
        # 300 distinct symbols: a0 + a1 + ... + a299
        many = " + ".join(f"a{i}" for i in range(300))
        with pytest.raises(SafeParseError):
            # parser with tight limits
            tight = SafeParser(max_atoms=100)
            tight.parse(many)


# ---------------------------------------------------------------------------
# F. Valid physics expressions (MUST parse successfully)
# ---------------------------------------------------------------------------

class TestValidPhysicsExpressions:

    def test_simple_symbol(self, parser):
        expr = parser.parse("x")
        assert isinstance(expr, sp.Expr)

    def test_polynomial(self, parser):
        expr = parser.parse("m * x_ddot + k * x")
        assert isinstance(expr, sp.Expr)

    def test_trig_expression(self, parser):
        expr = parser.parse("A * cos(omega * t + phi)")
        assert isinstance(expr, sp.Expr)

    def test_sqrt_expression(self, parser):
        expr = parser.parse("sqrt(k / m)")
        assert isinstance(expr, sp.Expr)

    def test_exp_expression(self, parser):
        gamma_sym = sp.Symbol("gamma", positive=True)
        omega_sym = sp.Symbol("omega", positive=True)
        t_sym = sp.Symbol("t", real=True)
        extra = {"gamma": gamma_sym, "omega": omega_sym, "t": t_sym}
        expr = parser.parse("exp(-gamma * t) * cos(omega * t)", extra_locals=extra)
        assert isinstance(expr, sp.Expr)

    def test_lagrangian_expression(self, parser):
        expr = parser.parse("Rational(1,2) * m * x_dot**2 - Rational(1,2) * k * x**2")
        assert isinstance(expr, sp.Expr)

    def test_field_theory_expression(self, parser):
        """Klein-Gordon Lagrangian density fragment."""
        expr = parser.parse("Rational(1,2) * (dphi_dt**2 - dphi_dx**2) - Rational(1,2) * m**2 * phi**2")
        assert isinstance(expr, sp.Expr)

    def test_constants_allowed(self, parser):
        expr = parser.parse("pi * r**2")
        assert isinstance(expr, sp.Expr)
        assert sp.pi in expr.atoms()

    def test_rational_number(self, parser):
        expr = parser.parse("Rational(1, 2) * m * v**2")
        assert isinstance(expr, sp.Expr)

    def test_equation_parsing(self, parser):
        expr = parser.parse_equation("m * x_ddot + k * x = 0")
        # Should simplify to m*x_ddot + k*x
        assert isinstance(expr, sp.Expr)

    def test_diff_notation_allowed(self, parser):
        """diff() is allowed as a function symbol in extra_locals."""
        t = sp.Symbol("t")
        x = sp.Function("x")
        extra = {"t": t, "x": x, "diff": sp.diff}
        expr = parser.parse("diff(x(t), t, 2)", extra_locals=extra)
        assert isinstance(expr, sp.Expr)


# ---------------------------------------------------------------------------
# G. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_string_rejected(self, parser):
        with pytest.raises(SafeParseError, match="Empty expression"):
            parser.parse("")

    def test_whitespace_only_rejected(self, parser):
        with pytest.raises(SafeParseError, match="Empty expression"):
            parser.parse("   ")

    def test_non_string_rejected(self, parser):
        with pytest.raises(SafeParseError, match="must be a string"):
            parser.parse(12345)  # type: ignore

    def test_invalid_symbol_name_rejected(self, parser):
        """make_symbol must reject names with special characters."""
        with pytest.raises(SafeParseError, match="valid identifier"):
            parser.make_symbol("x; import os")

    def test_valid_symbol_creation(self, parser):
        sym = parser.make_symbol("m", positive=True)
        assert sym.is_positive

    def test_double_equals_rejected(self, parser):
        """Python == in equation string must be rejected."""
        with pytest.raises(SafeParseError, match="Double =="):
            parser.parse_equation("x == 0")

    def test_invalid_extra_locals_key(self):
        """extra_symbols key with non-alphanumeric chars must fail construction."""
        with pytest.raises(SafeParseError, match="valid identifier"):
            SafeParser(extra_symbols={"x; rm -rf /": sp.Symbol("x")})

    def test_extra_locals_class_not_sympy(self):
        """extra_symbols value that is a Python module must fail."""
        import os
        with pytest.raises(SafeParseError, match="Python module"):
            SafeParser(extra_symbols={"os_module": os})



# ---------------------------------------------------------------------------
# H. Symbol name injection via free_symbols post-parse check
# ---------------------------------------------------------------------------

class TestPostParseSymbolCheck:

    def test_injected_symbol_name_blocked(self, parser):
        """
        SymPy allows creating Symbol('__import__("os")') — the post-parse
        symbol name check must catch this if sympify doesn't block it first.
        This is a defense-in-depth test.
        """
        # We test the _check_expr path directly by creating a bad expr
        bad_sym = sp.Symbol("__evil__")
        bad_expr = bad_sym + 1
        with pytest.raises(SafeParseError, match="disallowed characters"):
            parser._check_expr(bad_expr)

    def test_symbol_with_special_chars_blocked(self, parser):
        bad_sym = sp.Symbol("x@y")
        bad_expr = bad_sym * 2
        with pytest.raises(SafeParseError, match="disallowed characters"):
            parser._check_expr(bad_expr)


# ---------------------------------------------------------------------------
# I. Structural parser boundary
# ---------------------------------------------------------------------------

class TestStructuralParserBoundary:

    def test_attribute_access_rejected_structurally(self, parser):
        with pytest.raises(SafeParseError, match="direct allowlisted"):
            parser.parse("x.real")

    def test_subscript_access_rejected_structurally(self, parser):
        with pytest.raises(SafeParseError, match="Syntax node 'Subscript'"):
            parser.parse("x[0]")

    def test_keyword_arguments_rejected(self, parser):
        with pytest.raises(SafeParseError, match="Keyword arguments"):
            parser.parse("Rational(1, q=2)")

    def test_string_literal_rejected(self, parser):
        with pytest.raises(SafeParseError, match="Only numeric literals"):
            parser.parse("'not_math'")

    def test_arbitrary_extra_callable_rejected(self, parser):
        def evil(value):
            return value

        with pytest.raises(SafeParseError, match="not a permitted SymPy binding"):
            parser.parse("evil(x)", extra_locals={"evil": evil})

    def test_parser_does_not_call_sympify_on_source(self, monkeypatch):
        import automate.ir.safe_parser as safe_parser_module

        def fail_sympify(*args, **kwargs):
            raise AssertionError("untrusted source must never reach sympify")

        monkeypatch.setattr(safe_parser_module.sp, "sympify", fail_sympify)
        expr = SafeParser().parse("x + 1")
        assert isinstance(expr, sp.Expr)

    def test_bound_undefined_function_is_allowed(self, parser):
        t = sp.Symbol("t")
        x = sp.Function("x")
        expr = parser.parse("diff(x(t), t, 2)", extra_locals={"x": x, "t": t})
        assert expr != 0
        assert isinstance(expr, sp.Expr)


class TestIsolatedParsing:



    def test_safe_symbolic_function_application_is_allowed(self, parser):
        result = parser.parse("f(x) + g(t, x)")
        assert "f(x)" in str(result)
        assert "g(t, x)" in str(result)

    def test_isolated_parse_returns_equivalent_expression(self, parser):
        result = parser.parse_isolated("m*x**2 + k*x", timeout=3.0)
        assert sp.simplify(result - (sp.Symbol("m") * sp.Symbol("x")**2 + sp.Symbol("k") * sp.Symbol("x"))) == 0

    def test_isolated_equation_parse_returns_residual(self, parser):
        result = parser.parse_equation_isolated("m*x + k = 0", timeout=3.0)
        assert sp.simplify(result - (sp.Symbol("m") * sp.Symbol("x") + sp.Symbol("k"))) == 0

    def test_isolated_parse_rejects_nonpositive_timeout(self, parser):
        with pytest.raises(SafeParseError, match="greater than zero"):
            parser.parse_isolated("x + 1", timeout=0)

    def test_isolated_parse_preserves_bound_function(self):
        x = sp.Function("x")
        parser = SafeParser(extra_symbols={"x": x})
        result = parser.parse_isolated("diff(x(t), t, 2)", extra_locals={"x": x}, timeout=3.0)
        assert result == sp.diff(x(sp.Symbol("t")), sp.Symbol("t"), 2)


    def test_isolated_parse_enforces_output_size_limit(self, parser, monkeypatch):
        import automate.ir.safe_parser as safe_parser_module

        monkeypatch.setattr(safe_parser_module, "_MAX_RESULT_BYTES", 1)
        with pytest.raises(SafeParseError, match="output-size limit"):
            parser.parse_isolated("x + 1", timeout=3.0)


def test_safe_parser_matrix_construction_and_validation():
    from automate.ir.safe_parser import SafeParser
    import sympy as sp

    result = SafeParser().parse_isolated("Matrix((1,2),(3,4))")
    assert isinstance(result, sp.MatrixBase)
    assert result.det() == -2
