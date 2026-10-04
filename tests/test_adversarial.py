"""
Adversarial test suite for the Automate verification engine.

These tests verify that the backends REJECT incorrect mathematics.
They are the core anti-circularity guard: if any of these pass when they
should fail, a circularity regression has been introduced.

Principles enforced:
1. Wrong-sign Euler-Lagrange EoM must FAIL, not PASS.
2. Missing coordinates must return an UNSUPPORTED diagnostic, not silently pass.
3. Numerical energy drift > threshold must FAIL.
4. Lean fallback tautology must NOT give FORMALLY_PROVED for unrelated propositions.
5. Statistical backend must return NOT_APPLICABLE for non-empirical rules.
6. Numerical backend must return NOT_APPLICABLE for non-ODE rules.
7. SymPy backend must return NOT_APPLICABLE for numerical_simulation / empirical_inference.
8. AI proposal graph integrity: graph nodes must be unchanged on verification failure.
"""

import pytest
import copy
import sympy as sp

pytestmark = pytest.mark.adversarial

from automate.mechanics.lagrangian import LagrangianSystem
from automate.field_theory.variational import FieldTheoryAction
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.backend.dimension_backend import DimensionChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


# ---------------------------------------------------------------------------
# Helper: build a minimal two-node graph with one edge
# ---------------------------------------------------------------------------
def make_graph(
    in_expr: str,
    out_expr: str,
    rule: str,
    params: dict = None,
    edge_id: str = "edge_test",
    in_dim: str = "",
    out_dim: str = "",
) -> tuple:
    graph = DerivationGraph(id="adv_test", name="Adversarial Test Graph")
    in_node = DerivationNode(
        id="node_in",
        expression=MathematicalExpression(raw_str=in_expr, dimension=in_dim),
    )
    out_node = DerivationNode(
        id="node_out",
        expression=MathematicalExpression(raw_str=out_expr, dimension=out_dim),
    )
    graph.add_node(in_node)
    graph.add_node(out_node)
    edge = DerivationEdge(
        id=edge_id,
        input_nodes=["node_in"],
        output_nodes=["node_out"],
        transformation_rule=rule,
        justification="adversarial test",
        parameters=params or {},
    )
    graph.add_edge(edge)
    return graph, edge


# ===========================================================================
# 1. Wrong-sign Euler-Lagrange EoM must FAIL
# ===========================================================================

class TestWrongSignEulerLagrange:
    """
    The SHO Lagrangian L = 1/2 m x_dot^2 - 1/2 k x^2
    yields EoM  m x_ddot + k x = 0.
    A wrong-sign candidate  m x_ddot - k x = 0  must be REJECTED.
    """

    def test_wrong_sign_rejected_by_lagrangian_engine(self):
        sys = LagrangianSystem(
            lagrangian="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            coordinates=["x"],
            parameters={"m": "positive", "k": "positive"},
        )
        passed, details, _, err = sys.verify_euler_lagrange("m * x_ddot - k * x = 0")
        assert passed is False, "Wrong-sign EoM must NOT pass"
        assert err is not None

    def test_wrong_sign_rejected_by_sympy_backend(self):
        """SymPy backend must reject wrong-sign EoM at the graph level."""
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot - k * x",  # wrong sign
            rule="euler_lagrange",
            params={
                "coordinates": ["x"],
                "parameters": {"m": "positive", "k": "positive"},
            },
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False, "SymPy backend must reject wrong-sign EoM"
        assert report.status == VerificationStatus.FAILED

    def test_correct_eom_passes(self):
        """Correct EoM must still pass (sanity check)."""
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot + k * x",  # correct
            rule="euler_lagrange",
            params={
                "coordinates": ["x"],
                "parameters": {"m": "positive", "k": "positive"},
            },
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is True, "Correct EoM must pass"
        assert report.status == VerificationStatus.SYMBOLIC_CHECKED

    def test_pendulum_wrong_eom_rejected(self):
        """Wrong pendulum EoM (missing g·l factor) must be rejected."""
        sys = LagrangianSystem(
            lagrangian="1/2 * m * l**2 * theta_dot**2 + m * g * l * cos(theta)",
            coordinates=["theta"],
            parameters={"m": "positive", "l": "positive", "g": "positive"},
        )
        # Correct: m*l^2*theta_ddot + m*g*l*sin(theta) = 0
        # Wrong: m*l^2*theta_ddot + g*sin(theta) = 0  (missing l factor)
        passed, _, _, err = sys.verify_euler_lagrange("m * l**2 * theta_ddot + g * sin(theta) = 0")
        assert passed is False, "Pendulum EoM missing l factor must be rejected"

    def test_field_theory_wrong_mass_sign_rejected(self):
        """Klein-Gordon with wrong mass sign must be rejected by FieldTheoryAction."""
        t, x = sp.symbols("t x", real=True)
        m = sp.Symbol("m", positive=True)
        phi = sp.Function("phi")(t, x)
        dphi_dt = sp.diff(phi, t)
        dphi_dx = sp.diff(phi, x)
        # L = 1/2 (dphi/dt)^2 - 1/2 (dphi/dx)^2 - 1/2 m^2 phi^2
        L = sp.Rational(1, 2) * dphi_dt**2 - sp.Rational(1, 2) * dphi_dx**2 - sp.Rational(1, 2) * m**2 * phi**2
        action = FieldTheoryAction(
            lagrangian_density=L,
            fields=["phi"],
            coordinates=["t", "x"],
            parameters={"m": "positive"},
        )
        # Correct: phi_tt - phi_xx - m^2*phi = 0
        # Wrong: phi_tt - phi_xx + m^2*phi = 0  (sign flip on mass term)
        passed, _, _, err = action.verify_field_equation("d_t_d_t_phi - d_x_d_x_phi + m**2 * phi = 0")
        assert passed is False, "Klein-Gordon with wrong mass sign must be rejected"


# ===========================================================================
# 2. Missing coordinates → UNSUPPORTED diagnostic, not silent pass
# ===========================================================================

class TestMissingCoordinatesUnsupported:

    def test_euler_lagrange_without_coordinates_fails(self):
        """euler_lagrange rule without coordinates must return FAILED with UNSUPPORTED message."""
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot + k * x",
            rule="euler_lagrange",
            params={},  # NO coordinates
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False
        assert "UNSUPPORTED" in (report.error_message or ""), \
            f"Expected UNSUPPORTED in error, got: {report.error_message}"

    def test_conserve_energy_without_coordinates_fails(self):
        """conserve_energy without coordinates must return FAILED with UNSUPPORTED message."""
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="1/2 * m * x_dot**2 + 1/2 * k * x**2",
            rule="conserve_energy",
            params={},  # NO coordinates
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False
        assert "UNSUPPORTED" in (report.error_message or ""), \
            f"Expected UNSUPPORTED in error, got: {report.error_message}"

    def test_vary_action_without_fields_fails(self):
        """vary_action without fields must return FAILED with UNSUPPORTED message."""
        graph, edge = make_graph(
            in_expr="1/2 * phi_dot**2 - m**2 * phi**2 / 2",
            out_expr="phi_ddot + m**2 * phi = 0",
            rule="vary_action",
            params={},  # NO fields
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False
        assert "UNSUPPORTED" in (report.error_message or ""), \
            f"Expected UNSUPPORTED in error, got: {report.error_message}"


# ===========================================================================
# 3. Numerical backend: NOT_APPLICABLE for non-ODE rules
# ===========================================================================

class TestNumericalBackendNotApplicable:

    def test_algebraic_identity_not_applicable(self):
        """Numerical backend must return NOT_APPLICABLE for algebraic_identity."""
        graph, edge = make_graph(
            in_expr="x**2 + 2*x + 1",
            out_expr="(x + 1)**2",
            rule="algebraic_identity",
        )
        checker = NumericalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE
        assert report.passed is False

    def test_vary_action_not_applicable(self):
        """Numerical backend must return NOT_APPLICABLE for vary_action."""
        graph, edge = make_graph(
            in_expr="phi_dot**2 - m**2 * phi**2",
            out_expr="phi_ddot + m**2 * phi = 0",
            rule="vary_action",
        )
        checker = NumericalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE

    def test_empirical_inference_not_applicable(self):
        """Numerical backend must return NOT_APPLICABLE for empirical_inference."""
        graph, edge = make_graph(
            in_expr="A * cos(omega * t)",
            out_expr="omega ~ 2.0",
            rule="empirical_inference",
        )
        checker = NumericalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE


# ===========================================================================
# 4. Statistical backend: NOT_APPLICABLE for non-empirical rules
# ===========================================================================

class TestStatisticalBackendNotApplicable:

    def test_euler_lagrange_not_applicable(self):
        """Statistical backend must return NOT_APPLICABLE for euler_lagrange."""
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot + k * x",
            rule="euler_lagrange",
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE
        assert report.passed is False

    def test_numerical_simulation_not_applicable(self):
        """Statistical backend must return NOT_APPLICABLE for numerical_simulation."""
        graph, edge = make_graph(
            in_expr="m * x_ddot + k * x = 0",
            out_expr="trajectory",
            rule="numerical_simulation",
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE

    def test_empirical_inference_without_model_fails_with_unsupported(self):
        """Statistical backend must require model specification; no silent cosine default."""
        graph, edge = make_graph(
            in_expr="",  # no expression
            out_expr="omega ~ 2.0",
            rule="empirical_inference",
            params={},  # NO model specified
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False
        assert report.status == VerificationStatus.FAILED
        assert "UNSUPPORTED" in (report.error_message or ""), \
            f"Expected UNSUPPORTED in error, got: {report.error_message}"

    def test_cosine_model_explicit_passes(self):
        """Explicit cosine model with matching data must pass."""
        graph, edge = make_graph(
            in_expr="A * cos(omega * t + phi)",
            out_expr="A=1.0, omega=2.0, phi=0.0",
            rule="empirical_inference",
            params={"model": "cosine", "A": 1.0, "omega": 2.0, "phi": 0.0, "noise_std": 0.05},
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is True
        assert report.status == VerificationStatus.STATISTICALLY_CHECKED

    def test_exponential_decay_model(self):
        """Exponential decay model must fit and pass."""
        graph, edge = make_graph(
            in_expr="A * exp(-lambda * t)",
            out_expr="A=1.0, lambda=0.5",
            rule="empirical_inference",
            params={"model": "exponential_decay", "A": 1.0, "lambda": 0.5, "noise_std": 0.05},
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is True

    def test_wrong_model_on_cosine_data_fails(self):
        """Fitting a linear model to cosine data must produce poor R² and FAIL."""
        import numpy as np
        t = np.linspace(0, 10, 50).tolist()
        x = (np.cos(2.0 * np.linspace(0, 10, 50))).tolist()
        graph, edge = make_graph(
            in_expr="a * t + b",
            out_expr="a~0, b~1",
            rule="empirical_inference",
            params={
                "model": "linear",
                "t_data": t,
                "x_obs": x,
                "noise_std": 0.01,
            },
        )
        checker = StatisticalChecker()
        report = checker.verify_edge(edge, graph)
        # Linear model should NOT fit oscillatory cosine data
        assert report.passed is False, \
            "Linear model on cosine data must fail (poor R²)"


# ===========================================================================
# 5. SymPy backend: NOT_APPLICABLE for numerical/empirical rules
# ===========================================================================

class TestSymPyBackendNotApplicable:

    def test_numerical_simulation_not_applicable(self):
        """SymPy backend must return NOT_APPLICABLE for numerical_simulation."""
        graph, edge = make_graph(
            in_expr="m * x_ddot + k * x",
            out_expr="trajectory",
            rule="numerical_simulation",
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE

    def test_empirical_inference_not_applicable(self):
        """SymPy backend must return NOT_APPLICABLE for empirical_inference."""
        graph, edge = make_graph(
            in_expr="A * cos(omega * t)",
            out_expr="omega ~ 2.0",
            rule="empirical_inference",
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE


# ===========================================================================
# 6. Lean backend: tautology fallback removed
# ===========================================================================

class TestLeanBackendNoTautology:

    def test_unknown_rule_returns_not_applicable(self):
        """Unknown rules must return NOT_APPLICABLE, not FORMALLY_PROVED."""
        graph, edge = make_graph(
            in_expr="some_arbitrary_expression",
            out_expr="some_other_expression",
            rule="some_unknown_rule_xyz",
        )
        checker = LeanChecker()
        report = checker.verify_edge(edge, graph)
        # Must NOT be FORMALLY_PROVED
        assert report.status != VerificationStatus.FORMALLY_PROVED, \
            "Unknown rule must never return FORMALLY_PROVED"
        assert report.status == VerificationStatus.NOT_APPLICABLE

    def test_vary_action_not_applicable_in_lean(self):
        """vary_action has no Lean formalization yet; must return NOT_APPLICABLE."""
        graph, edge = make_graph(
            in_expr="phi_dot**2 - m**2 * phi**2",
            out_expr="phi_ddot + m**2 * phi = 0",
            rule="vary_action",
        )
        checker = LeanChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE
        assert report.passed is False

    def test_numerical_simulation_not_applicable_in_lean(self):
        """numerical_simulation has no Lean formalization; must return NOT_APPLICABLE."""
        graph, edge = make_graph(
            in_expr="m * x_ddot + k * x = 0",
            out_expr="x(t)",
            rule="numerical_simulation",
        )
        checker = LeanChecker()
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.NOT_APPLICABLE

    def test_lean_supported_rules_are_not_fabricated_without_lean(self):
        """
        If Lean 4 is not installed, the checker returns UNVERIFIED,
        not FORMALLY_PROVED. Verifies honesty when compiler absent.
        """
        checker = LeanChecker()
        if checker.is_available():
            pytest.skip("Lean 4 is installed; this test is for no-Lean environments only.")
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot + k * x",
            rule="euler_lagrange",
        )
        report = checker.verify_edge(edge, graph)
        assert report.status == VerificationStatus.UNVERIFIED
        assert report.passed is False


# ===========================================================================
# 7. AI proposal graph integrity: graph nodes must be unchanged on failure
# ===========================================================================

class TestGraphImmutabilityOnFailure:

    def test_failed_verification_does_not_corrupt_graph_nodes(self):
        """
        When symbolic verification fails (wrong-sign EoM),
        the graph nodes' expression strings must remain unchanged.
        """
        original_in_expr = "1/2 * m * x_dot**2 - 1/2 * k * x**2"
        original_out_expr = "m * x_ddot - k * x"  # wrong sign → will fail

        graph, edge = make_graph(
            in_expr=original_in_expr,
            out_expr=original_out_expr,
            rule="euler_lagrange",
            params={"coordinates": ["x"], "parameters": {"m": "positive", "k": "positive"}},
        )

        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)

        assert report.passed is False  # must fail

        # Node expressions must be unchanged
        assert graph.get_node("node_in").expression.raw_str == original_in_expr
        assert graph.get_node("node_out").expression.raw_str == original_out_expr

    def test_failed_verification_does_not_add_spurious_nodes(self):
        """
        Failed verification must not add new nodes to the graph.
        """
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot - k * x",
            rule="euler_lagrange",
            params={"coordinates": ["x"], "parameters": {"m": "positive", "k": "positive"}},
        )
        original_node_count = len(graph.nodes)

        checker = SymPyChecker()
        checker.verify_edge(edge, graph)

        assert len(graph.nodes) == original_node_count, \
            "Failed verification must not add spurious nodes"

    def test_failed_verification_records_failed_reason(self):
        """
        After a failed verification, edge.failed_reason must be populated.
        """
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot - k * x",
            rule="euler_lagrange",
            params={"coordinates": ["x"], "parameters": {"m": "positive", "k": "positive"}},
        )
        checker = SymPyChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is False
        assert edge.failed_reason is not None and len(edge.failed_reason) > 0, \
            "Failed edge must have a non-empty failed_reason"
        assert edge.status == VerificationStatus.FAILED


# ===========================================================================
# 8. Dimension backend: angle coordinates must not be treated as Length
# ===========================================================================

class TestDimensionBackendCoordinateAware:

    def test_euler_lagrange_with_angle_coordinate_does_not_fail(self):
        """
        For a pendulum with angular coordinate θ (dimensionless),
        specifying coordinate_dimension='angle' must not produce a spurious mismatch.
        """
        graph, edge = make_graph(
            in_expr="1/2 * m * l**2 * theta_dot**2 + m * g * l * cos(theta)",
            out_expr="m * l**2 * theta_ddot + m * g * l * sin(theta)",
            rule="euler_lagrange",
            params={"coordinate_dimension": "angle"},
            in_dim="dimensionless",
            out_dim="dimensionless",
        )
        checker = DimensionChecker()
        report = checker.verify_edge(edge, graph)
        # Both nodes are dimensionless → check should pass (skipped with note)
        assert report.passed is True, \
            f"Angle coordinate should not cause dimension mismatch. Error: {report.error_message}"

    def test_solve_harmonic_oscillator_angle_coordinate(self):
        """
        Trajectory in angle coordinate must be verified against dimensionless, not Length.
        """
        graph, edge = make_graph(
            in_expr="m * l**2 * theta_ddot + m * g * l * sin(theta)",
            out_expr="A * cos(omega * t + phi)",
            rule="solve_harmonic_oscillator",
            params={"coordinate_dimension": "angle"},
            in_dim="dimensionless",
            out_dim="dimensionless",
        )
        checker = DimensionChecker()
        report = checker.verify_edge(edge, graph)
        assert report.passed is True, \
            f"Angle trajectory should not cause dimension mismatch. Error: {report.error_message}"


# ===========================================================================
# 11. Checker capability bypass prevention: incompatible checker names rejected
# ===========================================================================

class TestCheckerCapabilityBypass:
    """
    Adversarial tests ensuring proposals cannot specify an incompatible checker
    (e.g., using 'dimension' or 'statistical' as a semantic proof of Euler-Lagrange)
    to bypass rigorous symbolic/formal verification.
    """

    def _make_graph_and_proposal(self, rule: str, checker: str):
        from automate.core.graph import DerivationGraph
        from automate.core.node import DerivationNode
        from automate.ir.ast import MathematicalExpression
        from automate.ai.schemas import DerivationProposal, CandidateNode

        graph = DerivationGraph(id="adv_cap_graph")
        in_node = DerivationNode(
            id="in_node",
            expression=MathematicalExpression(raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2")
        )
        graph.add_node(in_node)

        proposal = DerivationProposal(
            proposal_id="prop_cap_bypass",
            input_nodes=["in_node"],
            output_nodes=[
                CandidateNode(
                    id="out_node",
                    expression="m * x_ddot + k * x = 0",
                    node_kind="equation"
                )
            ],
            rule=rule,
            target_checker=checker,
            justification="Bypass test"
        )
        return graph, proposal

    def test_dimension_checker_rejected_for_euler_lagrange(self):
        """
        euler_lagrange allows only ['sympy', 'numerical', 'lean4'].
        Proposing target_checker='dimension' must be rejected before execution.
        """
        from automate.ai.validation import validate_ai_proposal
        from automate.ai.proposals import apply_and_verify_proposal
        graph, proposal = self._make_graph_and_proposal("euler_lagrange", "dimension")

        val_res = validate_ai_proposal(proposal.model_dump(), graph)
        assert not val_res.is_valid
        assert any("not allowed" in e for e in val_res.errors)

        exec_res = apply_and_verify_proposal(proposal, graph)
        assert not exec_res.success
        assert any("not allowed" in e for e in exec_res.errors)
        assert "out_node" not in graph.nodes

    def test_statistical_checker_rejected_for_euler_lagrange(self):
        """
        statistical backend cannot verify euler_lagrange; proposal must be rejected.
        """
        from automate.ai.validation import validate_ai_proposal
        from automate.ai.proposals import apply_and_verify_proposal
        graph, proposal = self._make_graph_and_proposal("euler_lagrange", "statistical")

        val_res = validate_ai_proposal(proposal.model_dump(), graph)
        assert not val_res.is_valid
        assert any("not allowed" in e for e in val_res.errors)

        exec_res = apply_and_verify_proposal(proposal, graph)
        assert not exec_res.success
        assert "out_node" not in graph.nodes

    def test_unknown_checker_rejected_in_validation(self):
        """
        Arbitrary checker names like 'quantum_oracle' must be rejected in validation.
        """
        from automate.ai.validation import validate_ai_proposal
        graph, proposal = self._make_graph_and_proposal("euler_lagrange", "quantum_oracle")

        val_res = validate_ai_proposal(proposal.model_dump(), graph)
        assert not val_res.is_valid
        assert any("Unknown checker 'quantum_oracle'" in e for e in val_res.errors)



# ===========================================================================
# 12. Dimension metadata must fail closed
# ===========================================================================

class TestUnknownDimensionMetadata:
    """Unknown unit/dimension declarations must not be interpreted as dimensionless."""

    def test_unknown_coordinate_dimension_rejected(self):
        graph, edge = make_graph(
            in_expr="1/2 * m * x_dot**2 - 1/2 * k * x**2",
            out_expr="m * x_ddot + k * x",
            rule="euler_lagrange",
            params={"coordinates": ["x"], "coordinate_dimension": "bogus_dimension"},
            in_dim="M*L^2*T^-2",
            out_dim="M*L*T^-2",
        )
        report = DimensionChecker().verify_edge(edge, graph)
        assert report.passed is False
        assert report.status == VerificationStatus.FAILED
        assert "Unknown coordinate_dimension" in (report.error_message or "")

    def test_unknown_coordinate_dimension_for_solution_rejected(self):
        graph, edge = make_graph(
            in_expr="m * x_ddot + k * x",
            out_expr="A * cos(omega * t + phi)",
            rule="solve_harmonic_oscillator",
            params={"coordinate_dimension": "bogus_dimension"},
            in_dim="M*L*T^-2",
            out_dim="L",
        )
        report = DimensionChecker().verify_edge(edge, graph)
        assert report.passed is False
        assert report.status == VerificationStatus.FAILED
        assert "Unknown coordinate_dimension" in (report.error_message or "")
