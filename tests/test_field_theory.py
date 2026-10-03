"""
Tests for field-theory actions, differential geometry primitives, and functional calculus.
"""

import pytest
from automate.ir.tensors import TensorIndex
from automate.ir.actions import (
    Manifold,
    CoordinateChart,
    MetricTensor,
    ChristoffelSymbols,
    RiemannTensor,
    RicciTensor,
    RicciScalar,
    EinsteinTensor,
    IntegrationMeasure,
    LagrangianDensity,
    ActionFunctional,
    FunctionalDerivative,
    FieldEquation,
)
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.ir.ast import MathematicalExpression, ActionNode, MeasureNode
from automate.core.status import VerificationStatus
from automate.theory.rules import RuleRegistry


def test_differential_geometry_primitives():
    # 4D Lorentzian manifold
    manifold = Manifold(name="Spacetime", dimension=4, signature="(-,+,+,+)")
    assert manifold.dimension == 4
    assert manifold.signature == "(-,+,+,+)"

    chart = CoordinateChart(coordinates=["t", "x", "y", "z"])
    assert len(chart.coordinates) == 4

    metric = MetricTensor()
    assert metric.symmetry == "symmetric"
    assert len(metric.indices) == 2

    gamma = ChristoffelSymbols()
    assert gamma.upper_index.position == "upper"
    assert len(gamma.lower_indices) == 2
    assert gamma.symmetric_lower is True

    riemann = RiemannTensor()
    assert len(riemann.indices) == 4
    assert riemann.indices[0].position == "upper"

    ricci = RicciTensor()
    assert len(ricci.indices) == 2
    assert ricci.is_symmetric is True
    assert ricci.dimension == "L^-2"

    scalar_r = RicciScalar()
    assert scalar_r.rank == 0
    assert scalar_r.dimension == "L^-2"

    einstein_g = EinsteinTensor()
    assert len(einstein_g.indices) == 2
    assert einstein_g.dimension == "L^-2"


def test_einstein_hilbert_action():
    # S_EH = 1/(16*pi*G) * \int d^4x \sqrt{-g} R
    measure = IntegrationMeasure(
        coordinates=["t", "x", "y", "z"],
        volume_form="d^4x",
        metric_determinant_factor="sqrt(-g)",
        dimension="L^4"
    )

    lagrangian = LagrangianDensity(
        name="L_grav",
        fields=["g"],
        potential_term="R",
        dimension="M*L^-1*T^-2"
    )

    action = ActionFunctional(
        name="S_EH",
        prefactor="1 / (16 * pi * G)",
        lagrangian_density=lagrangian,
        measure=measure,
        assumptions=["asymptotically_flat", "vanishing_boundary_variation"]
    )

    assert action.dimension == "M*L^2*T^-1"
    assert action.prefactor == "1 / (16 * pi * G)"
    assert len(action.assumptions) == 2


def test_functional_derivative_and_field_equations():
    # delta S / delta g^{mu nu} = 0 -> G_{mu nu} = 8 pi G T_{mu nu}
    variation = FunctionalDerivative(
        action_name="S_EH",
        target_field="g^{mu nu}",
        vanishing_boundary_assumptions=["delta g = 0 on boundary"]
    )
    assert variation.target_field == "g^{mu nu}"

    mu = TensorIndex(symbol="mu", position="lower")
    nu = TensorIndex(symbol="nu", position="lower")

    field_eq = FieldEquation(
        name="EinsteinFieldEquations",
        action="S_EH",
        field="g",
        lhs_expression="G_{mu nu}",
        rhs_expression="8 * pi * G * T_{mu nu}",
        free_indices=[mu, nu]
    )
    assert field_eq.lhs_expression == "G_{mu nu}"
    assert field_eq.rhs_expression == "8 * pi * G * T_{mu nu}"
    assert len(field_eq.free_indices) == 2


def test_field_theory_graph_integration():
    # Embed in DerivationGraph
    graph = DerivationGraph(id="gr_derivation", name="General Relativity Derivation")

    # Node 1: Action S_EH
    n1 = DerivationNode(
        id="action_eh",
        expression=MathematicalExpression(
            raw_str="S_EH = 1/(16*pi*G) * integral(d^4x * sqrt(-g) * R)",
            dimension="M*L^2*T^-1",
            ast_node=ActionNode(
                name="S_EH",
                lagrangian_density={"fields": ["g"], "term": "R"},
                measure=MeasureNode().model_dump()
            )
        ),
        domain="General Relativity",
        status=VerificationStatus.PARSED
    )
    graph.add_node(n1)

    # Node 2: Field equation G_{\mu \nu} = 0 (vacuum)
    n2 = DerivationNode(
        id="einstein_vacuum",
        expression=MathematicalExpression(
            raw_str="G_{mu nu} = 0",
            dimension="L^-2"
        ),
        domain="General Relativity"
    )
    graph.add_node(n2)

    # Variational step edge
    reg = RuleRegistry()
    rule = reg.get_rule("vary_action")
    assert rule is not None

    edge = DerivationEdge(
        id="vary_eh",
        input_nodes=["action_eh"],
        output_nodes=["einstein_vacuum"],
        transformation_rule="vary_action",
        justification="Principle of stationary action with vanishing boundary variations",
        side_conditions=["vanishing_boundary_variations"],
        status=VerificationStatus.UNVERIFIED
    )
    graph.add_edge(edge)

    assert graph.validate_dag() is True
    assert graph.topological_sort() == ["action_eh", "einstein_vacuum"]
    assert graph.is_fully_verified() is False
    assert graph.nodes["action_eh"].status == VerificationStatus.PARSED
