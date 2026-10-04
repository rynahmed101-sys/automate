"""Tests for graph-bound Lean proposition translation."""

import pytest

from automate.backend.graph_to_lean import (
    GraphToLeanTranslationError,
    translate_edge_claim,
    translate_node_expression,
)


def test_integer_expression_translation_returns_binders_and_expression():
    code, names = translate_node_expression("x**2 + 2*x + 1")
    assert ": Int" not in code
    assert "x" in code
    assert names == ["x"]


def test_equation_translation_preserves_relation():
    code, names = translate_node_expression("m * a + k * x = 0")
    assert " = " in code
    assert "m" in code
    assert "a" in code
    assert "k" in code
    assert "x" in code
    assert names == ["a", "k", "m", "x"]


@pytest.mark.parametrize("raw,operator", [
    ("x != 0", "!="),
    ("x > 0", ">"),
    ("x < 0", "<"),
    ("x >= 0", ">="),
    ("x <= 0", "<="),
])
def test_supported_relational_translation(raw, operator):
    code, names = translate_node_expression(raw)
    assert operator in code
    assert names == ["x"]


def test_graph_edge_translation_is_not_rule_name_inference():
    claim = translate_edge_claim(
        "algebraic_identity",
        ["x**2 + 2*x + 1"],
        ["(x + 1)**2"],
    )

    assert claim.relation == "equality"
    assert "x" in claim.binders
    assert "=" in claim.proposition
    assert claim.source_nodes[0]["raw_expression"] == "x**2 + 2*x + 1"


def test_generic_equivalent_relation_requires_one_input_and_output():
    claim = translate_edge_claim(
        "equivalent",
        ["x + 1"],
        ["1 + x"],
    )
    assert claim.relation == "equality"
    assert claim.binders == ["x"]


def test_implication_translation_builds_hypotheses_from_graph_nodes():
    claim = translate_edge_claim(
        "implies",
        ["x >= 0", "y >= 0"],
        ["x + y >= 0"],
    )

    assert claim.relation == "implication"
    assert "->" in claim.proposition
    assert claim.binders == ["x", "y"]


def test_unsupported_physical_rule_is_rejected_without_canned_theorem():
    with pytest.raises(GraphToLeanTranslationError, match="no generic graph-to-Lean"):
        translate_edge_claim(
            "euler_lagrange",
            ["L"],
            ["E"],
        )


def test_unsupported_math_construct_is_explicitly_rejected():
    with pytest.raises(GraphToLeanTranslationError):
        translate_node_expression("sin(x)")


def test_algebraic_identity_rejects_equation_operands():
    with pytest.raises(GraphToLeanTranslationError, match="expects arithmetic expressions"):
        translate_edge_claim(
            "algebraic_identity",
            ["x = y"],
            ["y = x"],
        )
