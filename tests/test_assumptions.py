"""
Tests for First-Class Assumption Tracking and Sensitivity Analysis.
"""

import pytest
from automate.ir.assumptions import Assumption, AssumptionRegistry
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.ir.ast import MathematicalExpression


def test_assumption_creation():
    asm = Assumption(
        id="asm_pos_m",
        description="Mass is positive",
        category="positivity",
        formal_predicate="m > 0"
    )
    assert asm.id == "asm_pos_m"
    assert asm.active is True
    assert asm.formal_predicate == "m > 0"


def test_graph_assumption_inheritance_and_sensitivity():
    graph = DerivationGraph(id="test_graph")

    # Add assumptions
    a1 = Assumption(id="asm_1", description="Axiom 1", formal_predicate="P1")
    a2 = Assumption(id="asm_2", description="Axiom 2", formal_predicate="P2")
    graph.add_assumption(a1)
    graph.add_assumption(a2)

    # Node 1 depends on asm_1
    n1 = DerivationNode(
        id="N1",
        expression=MathematicalExpression(raw_str="E1"),
        assumptions=["asm_1"]
    )
    # Node 2 depends on asm_2
    n2 = DerivationNode(
        id="N2",
        expression=MathematicalExpression(raw_str="E2"),
        assumptions=["asm_2"]
    )
    # Node 3 derived from N1 and N2
    n3 = DerivationNode(
        id="N3",
        expression=MathematicalExpression(raw_str="E3"),
        assumptions=[]
    )
    # Node 4 derived from N3
    n4 = DerivationNode(
        id="N4",
        expression=MathematicalExpression(raw_str="E4"),
        assumptions=[]
    )

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    # Edges: N1, N2 -> N3 -> N4
    e1 = DerivationEdge(
        id="E1",
        input_nodes=["N1", "N2"],
        output_nodes=["N3"],
        transformation_rule="combine",
        justification="Step 1"
    )
    e2 = DerivationEdge(
        id="E2",
        input_nodes=["N3"],
        output_nodes=["N4"],
        transformation_rule="derive",
        justification="Step 2"
    )

    graph.add_edge(e1)
    graph.add_edge(e2)

    # Transitive assumption checking
    n4_asms = graph.compute_inherited_assumptions("N4")
    assert n4_asms == {"asm_1", "asm_2"}

    # Query: which nodes depend on asm_1?
    dep_on_1 = graph.query_nodes_dependent_on("asm_1")
    assert set(dep_on_1) == {"N1", "N3", "N4"}

    # Simulate removal of asm_1
    impact = graph.simulate_assumption_removal("asm_1")
    assert impact["dropped_assumption"] == "asm_1"
    assert set(impact["surviving_nodes"]) == {"N2"}
    assert set(impact["invalidated_nodes"]) == {"N1", "N3", "N4"}
    assert set(impact["invalidated_edges"]) == {"E1", "E2"}
    assert impact["survival_ratio"] == 0.25
