"""Tests for independent Cadabra result comparison."""

from automate.ir.tensors import TensorEquation, TensorExpression, TensorIndex, TensorProduct, TensorQuantity
from automate.tensors.cadabra_verification import (
    independent_structural_equation_result,
    independent_structural_result,
    verify_translated_expression,
)


def idx(symbol, position="lower"):
    return TensorIndex(symbol=symbol, position=position)


def expr():
    return TensorExpression(
        terms=[[idx("a"), idx("b", "upper"), idx("b")]],
        products=[TensorProduct(factors=[
            TensorQuantity(name="R", indices=[idx("a"), idx("b", "upper")]),
            TensorQuantity(name="v", indices=[idx("b")]),
        ])],
    )


def test_independent_renderer_does_not_depend_on_translation():
    assert independent_structural_result(expr()) == "R_{a}^{b} v_{b}"


def test_independent_equation_renderer():
    equation = TensorEquation(
        lhs=expr(),
        rhs=TensorExpression(
            terms=[[idx("a")]],
            products=[TensorProduct(factors=[TensorQuantity(name="w", indices=[idx("a")])])],
        ),
    )
    assert independent_structural_equation_result(equation) == "R_{a}^{b} v_{b} = w_{a}"


def test_verified_path_generates_internal_comparison_target(monkeypatch):
    captured = {}

    def fake_run(source, *, expected_output=None, sandbox_limits=None, claim_fingerprint_sha256=None, comparison_target_source="caller_supplied"):
        captured.update({
            "source": source,
            "expected_output": expected_output,
            "claim_fingerprint_sha256": claim_fingerprint_sha256,
            "comparison_target_source": comparison_target_source,
        })
        return {
            "execution_status": "COMPLETED",
            "independence_class": "DIFFERENT_ENGINE",
        }

    monkeypatch.setattr(
        "automate.tensors.cadabra_verification.run_cadabra_script",
        fake_run,
    )
    result = verify_translated_expression(expr())
    assert result["independence_class"] == "DIFFERENT_ENGINE"
    assert captured["expected_output"] == "R_{a}^{b} v_{b}"
    assert captured["claim_fingerprint_sha256"]
    assert captured["comparison_target_source"] == "independent_renderer"
    assert "print(str(ex))" in captured["source"]
