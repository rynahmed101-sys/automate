"""
Tests for canonical IR AST serialization, JSON round-trips, and certificate manifest integrity.
"""

import hashlib
import json
from pathlib import Path
import pytest

from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.ir.ast import (
    MathematicalExpression,
    ScalarNode,
    DerivativeNode,
    TensorNode,
    ActionNode,
    MeasureNode,
    FieldNode,
    OperatorNode,
)
from automate.ir.tensors import TensorIndex
from automate.core.status import VerificationStatus
from automate.theory.parser import parse_theory_file


def test_typed_ast_nodes_serialization_roundtrip():
    # 1. ScalarNode
    s = ScalarNode(value="m", dimension="M", is_constant=False)
    s_dict = s.model_dump()
    assert s_dict["kind"] == "scalar"
    assert s_dict["value"] == "m"
    s_back = ScalarNode(**s_dict)
    assert s_back.value == s.value

    # 2. DerivativeNode
    d = DerivativeNode(
        target={"kind": "variable", "name": "x"},
        wrt=["t", "t"],
        order=2,
        deriv_type="time_dot"
    )
    d_dict = d.model_dump()
    assert d_dict["kind"] == "derivative"
    assert d_dict["deriv_type"] == "time_dot"
    d_back = DerivativeNode(**d_dict)
    assert d_back.order == 2
    assert d_back.deriv_type == "time_dot"
    assert d_back.wrt == ["t", "t"]

    # 3. TensorNode
    t = TensorNode(
        name="R",
        indices=["mu", "nu"],
        contravariant=[False, False],
        dimension="L^-2",
        symmetry="symmetric"
    )
    t_dict = t.model_dump()
    assert t_dict["kind"] == "tensor"
    assert len(t_dict["indices"]) == 2
    t_back = TensorNode(**t_dict)
    typed_indices = t_back.get_typed_indices()
    assert len(typed_indices) == 2
    assert typed_indices[0].symbol == "mu"
    assert typed_indices[0].position == "lower"

    # 4. ActionNode and MeasureNode
    m = MeasureNode(coordinates=["t", "x", "y", "z"], metric_determinant="sqrt(-g)", dimension="L^4")
    a = ActionNode(name="S_EH", lagrangian_density={"fields": ["g"], "term": "R"}, measure=m.model_dump())
    a_dict = a.model_dump()
    assert a_dict["kind"] == "action"
    a_back = ActionNode(**a_dict)
    assert a_back.name == "S_EH"
    assert a_back.measure["metric_determinant"] == "sqrt(-g)"


def test_derivation_graph_json_roundtrip():
    graph = DerivationGraph(id="roundtrip_test", name="Roundtrip Test")

    expr1 = MathematicalExpression(
        raw_str="E = mc^2",
        dimension="M*L^2*T^-2",
        latex="E = mc^2",
        ast=ScalarNode(value="E", dimension="M*L^2*T^-2").model_dump()
    )
    node1 = DerivationNode(id="n1", expression=expr1, domain="relativity", status=VerificationStatus.SYMBOLIC_CHECKED)

    expr2 = MathematicalExpression(raw_str="p = mv", dimension="M*L*T^-1")
    node2 = DerivationNode(id="n2", expression=expr2, domain="mechanics", status=VerificationStatus.SYMBOLIC_CHECKED)

    graph.add_node(node1)
    graph.add_node(node2)

    cert = DerivationCertificate(
        rule_name="identity",
        steps=[{"step": 1, "expr": "E = mc^2"}],
        execution_time_ms=1.5
    )
    edge = DerivationEdge(
        id="e1",
        input_nodes=["n1"],
        output_nodes=["n2"],
        transformation_rule="identity",
        justification="Test justification",
        status=VerificationStatus.SYMBOLIC_CHECKED,
        certificate=cert
    )
    graph.add_edge(edge)

    # Serialize to JSON and reload
    json_str = graph.to_json()
    graph_reloaded = DerivationGraph.from_json(json_str)

    assert graph_reloaded.id == "roundtrip_test"
    assert len(graph_reloaded.nodes) == 2
    assert len(graph_reloaded.edges) == 1
    assert graph_reloaded.nodes["n1"].expression.raw_str == "E = mc^2"
    assert graph_reloaded.nodes["n1"].expression.ast["value"] == "E"
    assert graph_reloaded.edges["e1"].certificate.rule_name == "identity"
    assert graph_reloaded.edges["e1"].status == VerificationStatus.SYMBOLIC_CHECKED
