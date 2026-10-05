"""Tests for strict graph AST -> canonical Tensor IR conversion."""

import pytest

from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode, MathematicalExpression
from automate.ir.tensors import TensorEquation
from automate.tensors.graph_translation import (
    graph_equation_node_to_tensor_ir,
    graph_node_to_tensor_ir,
)


def _tensor(name, indices, contravariant):
    return {
        "kind": "tensor",
        "name": name,
        "indices": indices,
        "contravariant": contravariant,
    }


def _node(node_id, ast):
    return DerivationNode(
        id=node_id,
        expression=MathematicalExpression(raw_str="opaque", ast=ast),
        node_kind="tensor",
    )


def test_graph_tensor_ast_preserves_factor_identity_and_variance():
    graph = DerivationGraph(id="g")
    graph.add_node(_node(
        "n",
        {
            "kind": "binary_op",
            "op": "mul",
            "left": _tensor("R", ["a", "b"], [False, True]),
            "right": _tensor("v", ["b"], [False]),
        },
    ))

    expression = graph_node_to_tensor_ir(graph, "n")
    assert [factor.name for factor in expression.products[0].factors] == ["R", "v"]
    assert [(i.symbol, i.position) for i in expression.products[0].indices] == [
        ("a", "lower"), ("b", "upper"), ("b", "lower")
    ]


def test_graph_tensor_ast_rejects_unrepresentable_operation():
    graph = DerivationGraph(id="g")
    graph.add_node(_node(
        "n",
        {"kind": "binary_op", "op": "div",
         "left": _tensor("A", ["a"], [False]),
         "right": _tensor("B", [], [])},
    ))
    with pytest.raises(ValueError, match="unsupported binary operation"):
        graph_node_to_tensor_ir(graph, "n")


def test_graph_tensor_ast_rejects_missing_ast_instead_of_parsing_raw_text():
    graph = DerivationGraph(id="g")
    graph.add_node(DerivationNode(
        id="n",
        expression=MathematicalExpression(raw_str="R_{a}^{b} v_{b}"),
        node_kind="tensor",
    ))
    with pytest.raises(ValueError, match="populated"):
        graph_node_to_tensor_ir(graph, "n")


def test_graph_equation_ast_builds_valid_tensor_equation():
    graph = DerivationGraph(id="g")
    graph.add_node(_node(
        "n",
        {
            "kind": "equation",
            "lhs": {
                "kind": "binary_op",
                "op": "mul",
                "left": _tensor("R", ["a", "b"], [False, True]),
                "right": _tensor("v", ["b"], [False]),
            },
            "rhs": _tensor("w", ["a"], [False]),
        },
    ))
    equation = graph_equation_node_to_tensor_ir(graph, "n")
    assert isinstance(equation, TensorEquation)
    assert equation.free_index_signature == [("a", "lower", None)]


def test_graph_to_cadabra_boundary_binds_canonical_ir_fingerprint(monkeypatch):
    graph = DerivationGraph(id="g")
    graph.add_node(_node(
        "n",
        {
            "kind": "binary_op",
            "op": "mul",
            "left": _tensor("R", ["a", "b"], [False, True]),
            "right": _tensor("v", ["b"], [False]),
        },
    ))
    captured = {}

    def fake_run(source, *, expected_output=None, sandbox_limits=None, claim_fingerprint_sha256=None, comparison_target_source="caller_supplied"):
        captured["source"] = source
        captured["expected_output"] = expected_output
        captured["claim"] = claim_fingerprint_sha256
        captured["comparison_target_source"] = comparison_target_source
        return {
            "execution_status": "COMPLETED",
            "independence_class": "DIFFERENT_ENGINE",
        }

    monkeypatch.setattr(
        "automate.tensors.cadabra_verification.run_cadabra_script",
        fake_run,
    )
    from automate.tensors.cadabra_verification import verify_graph_tensor_node_with_cadabra

    result = verify_graph_tensor_node_with_cadabra(graph, "n")
    assert result["independence_class"] == "DIFFERENT_ENGINE"
    assert captured["claim"]
    assert captured["comparison_target_source"] == "independent_renderer"
    assert len(captured["claim"]) == 64
    assert captured["expected_output"] == "R_{a}^{b} v_{b}"
    assert "ex := R_{a}^{b} v_{b}:" in captured["source"]
