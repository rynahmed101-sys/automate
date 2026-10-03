"""
Tests for DerivationGraph DAG operations, topological sorting, and certificate expansion.
"""

import pytest
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.ir.ast import MathematicalExpression
from automate.core.status import VerificationStatus


def test_dag_cycle_detection():
    graph = DerivationGraph(id="cycle_test")

    n1 = DerivationNode(id="A", expression=MathematicalExpression(raw_str="a"))
    n2 = DerivationNode(id="B", expression=MathematicalExpression(raw_str="b"))
    graph.add_node(n1)
    graph.add_node(n2)

    # A -> B
    graph.add_edge(DerivationEdge(
        id="e1",
        input_nodes=["A"],
        output_nodes=["B"],
        transformation_rule="rule1",
        justification="just1"
    ))
    assert graph.validate_dag() is True
    assert graph.topological_sort() == ["A", "B"]

    # B -> A creates cycle!
    graph.add_edge(DerivationEdge(
        id="e2",
        input_nodes=["B"],
        output_nodes=["A"],
        transformation_rule="rule2",
        justification="just2"
    ))
    assert graph.validate_dag() is False
    with pytest.raises(ValueError):
        graph.topological_sort()


def test_lossless_macro_expansion():
    graph = DerivationGraph(id="expansion_test")

    n1 = DerivationNode(id="A", expression=MathematicalExpression(raw_str="L"))
    n2 = DerivationNode(id="B", expression=MathematicalExpression(raw_str="EoM"))
    graph.add_node(n1)
    graph.add_node(n2)

    # Edge with multi-step certificate
    cert = DerivationCertificate(
        rule_name="euler_lagrange",
        steps=[
            {"step": 1, "operation": "dL/dx_dot", "expr": "m*x_dot", "description": "Partial velocity"},
            {"step": 2, "operation": "d/dt(dL/dx_dot)", "expr": "m*x_ddot", "description": "Time derivative"},
            {"step": 3, "operation": "dL/dx", "expr": "-k*x", "description": "Partial coordinate"}
        ]
    )

    edge = DerivationEdge(
        id="edge_macro",
        input_nodes=["A"],
        output_nodes=["B"],
        transformation_rule="euler_lagrange",
        justification="Action Principle",
        certificate=cert
    )
    graph.add_edge(edge)

    # Expand certificate
    subgraph = graph.expand_edge_certificate("edge_macro")
    assert subgraph is not None
    # Input node A + 3 certificate nodes + Output node B = 5 nodes
    assert len(subgraph.nodes) == 5
    assert len(subgraph.edges) == 4
    assert subgraph.validate_dag() is True
