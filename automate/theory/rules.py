"""
Structured Local Rule Registry for Automate.
Exposes rich metadata, required assumptions, side conditions, verification backends,
and automatic verification obligation generation across transformation steps.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleDefinition(BaseModel):
    """
    Formal transformation rule definition.
    """
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    category: str = Field(
        default="algebra",
        description="Category: algebra, calculus, tensors, variational, differential_equations, numerics, statistics"
    )
    description: str = Field(..., description="Mathematical explanation or citation")
    domain: str = Field(default="general_physics")
    inputs: List[str] = Field(default_factory=list, description="Expected input types/roles")
    outputs: List[str] = Field(default_factory=list, description="Expected output types/roles")
    required_assumptions: List[str] = Field(default_factory=list)
    side_conditions: List[str] = Field(default_factory=list, description="Prerequisite physical conditions")
    default_obligations: List[Dict[str, Any]] = Field(default_factory=list)
    reversible: bool = Field(default=False)
    implementation_backend: str = Field(default="sympy")
    formal_proof_available: bool = Field(default=False)
    symbolic_checker_available: bool = Field(default=True)
    citation: Optional[str] = None

    def generate_obligations(self, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Synthesizes concrete verification obligations given step parameters.
        """
        obligations = list(self.default_obligations)
        params = parameters or {}
        if self.rule_id == "divide_both_sides":
            divisor = params.get("divisor", "x")
            obligations.append({
                "type": "non_zero_constraint",
                "claim": f"{divisor} != 0",
                "description": f"Division requires non-zero denominator '{divisor}'"
            })
        elif self.rule_id == "index_contract":
            pair = params.get("index_pair", ("mu", "mu"))
            obligations.append({
                "type": "index_contraction_legality",
                "claim": f"valid_contraction({pair[0]}, {pair[1]})",
                "description": f"Einstein contraction requires one contravariant and one covariant index on '{pair[0]}'"
            })
        elif self.rule_id == "differentiate_both_sides":
            var = params.get("wrt", "t")
            obligations.append({
                "type": "smoothness_constraint",
                "claim": f"differentiable_wrt({var})",
                "description": f"Differentiating both sides requires target expression to be differentiable wrt '{var}'"
            })
        elif self.rule_id == "vary_action":
            field = params.get("field", "phi")
            obligations.append({
                "type": "stationary_action_principle",
                "claim": f"delta_S / delta_{field} == 0",
                "description": f"Euler-Lagrange field equation derived from stationary action variation"
            })
        return obligations


class RuleRegistry:
    """
    Central registry of approved and verified transformation rules.
    """
    def __init__(self):
        self._rules: Dict[str, RuleDefinition] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        # 1. Variational Action Rules
        self.register(RuleDefinition(
            rule_id="euler_lagrange",
            name="Euler-Lagrange Equation",
            category="variational",
            description="Derives equations of motion from action principle: d/dt(dL/dq_dot) - dL/dq = 0",
            domain="classical_mechanics",
            inputs=["Lagrangian"],
            outputs=["Equation of Motion"],
            required_assumptions=["asm_smooth_trajectory"],
            side_conditions=["asm_smooth_trajectory"],
            default_obligations=[{
                "type": "stationary_action",
                "claim": "d/dt(dL/dv) - dL/dx == 0",
                "description": "Hamilton's principle stationary action condition"
            }],
            implementation_backend="sympy",
            formal_proof_available=True,
            symbolic_checker_available=True,
            citation="Hamilton's Principle / Calculus of Variations"
        ))

        self.register(RuleDefinition(
            rule_id="vary_action",
            name="Functional Variation of Action",
            category="variational",
            description="Varies action functional with respect to dynamical field to derive field equations: delta S / delta phi = 0",
            domain="field_theory",
            inputs=["Action"],
            outputs=["Field Equation"],
            required_assumptions=["vanishing_boundary_variations"],
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        # 2. Conservation Laws
        self.register(RuleDefinition(
            rule_id="conserve_energy",
            name="Noether Energy Conservation",
            category="conservation",
            description="Derives Jacobi energy function E = sum(p_i q_dot_i) - L and verifies dE/dt = 0 on-shell",
            domain="classical_mechanics",
            inputs=["Lagrangian", "Equation of Motion"],
            outputs=["Conserved Energy"],
            required_assumptions=["time_translation_invariance"],
            side_conditions=["asm_pos_mass", "asm_pos_k", "asm_conservative"],
            default_obligations=[{
                "type": "on_shell_invariance",
                "claim": "v * (m * a + k * x) == 0",
                "description": "Total energy derivative vanishes along equations of motion"
            }],
            implementation_backend="lean4",
            formal_proof_available=True,
            symbolic_checker_available=True,
            citation="Noether's Theorem"
        ))

        # 3. Algebraic Rules
        self.register(RuleDefinition(
            rule_id="divide_both_sides",
            name="Divide Both Sides",
            category="algebra",
            description="Divides both sides of an equation by a non-zero algebraic term",
            domain="mathematics",
            reversible=True,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        self.register(RuleDefinition(
            rule_id="differentiate_both_sides",
            name="Differentiate Both Sides",
            category="calculus",
            description="Differentiates both sides of an equality with respect to an independent variable",
            domain="mathematics",
            reversible=False,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        self.register(RuleDefinition(
            rule_id="substitute",
            name="Substitute Expression",
            category="algebra",
            description="Replaces a symbol or sub-expression with an equivalent known equality",
            domain="mathematics",
            reversible=True,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        self.register(RuleDefinition(
            rule_id="simplify",
            name="Algebraic Simplification",
            category="algebra",
            description="Simplifies an algebraic expression into canonical minimal form",
            domain="mathematics",
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        # 4. Tensor Calculus Rules
        self.register(RuleDefinition(
            rule_id="index_contract",
            name="Einstein Index Contraction",
            category="tensors",
            description="Contracts one upper and one lower index using Einstein summation convention",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        self.register(RuleDefinition(
            rule_id="raise_index",
            name="Raise Tensor Index",
            category="tensors",
            description="Raises a covariant tensor index using the inverse metric g^{mu nu}",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        self.register(RuleDefinition(
            rule_id="lower_index",
            name="Lower Tensor Index",
            category="tensors",
            description="Lowers a contravariant tensor index using the metric g_{mu nu}",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        # 5. Differential Equations & Solutions
        self.register(RuleDefinition(
            rule_id="solve_harmonic_oscillator",
            name="Harmonic Oscillator General Solution",
            category="differential_equations",
            description="General analytical solution of linear 2nd-order ODE: x(t) = A*cos(omega*t + phi)",
            domain="classical_mechanics",
            inputs=["Equation of Motion"],
            outputs=["Analytical Solution"],
            required_assumptions=["asm_pos_mass", "asm_pos_k"],
            side_conditions=["asm_pos_mass", "asm_pos_k"],
            default_obligations=[{
                "type": "ode_substitution",
                "claim": "m * (-omega^2 * x) + k * x == 0",
                "description": "Harmonic ansatz satisfies equation of motion"
            }],
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            citation="Linear Ordinary Differential Equations"
        ))

        self.register(RuleDefinition(
            rule_id="algebraic_identity",
            name="Algebraic Identity",
            category="algebra",
            description="Symbolic simplification, expansion, or algebraic equality",
            domain="mathematics",
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True
        ))

        # 6. Computational & Experimental
        self.register(RuleDefinition(
            rule_id="numerical_simulation",
            name="Numerical IVP Integration",
            category="numerics",
            description="Numerical integration of equations of motion using Runge-Kutta ODE solver",
            domain="computational_physics",
            implementation_backend="numerical",
            formal_proof_available=False,
            symbolic_checker_available=False
        ))

        self.register(RuleDefinition(
            rule_id="empirical_inference",
            name="Empirical Parameter Estimation",
            category="statistics",
            description="Non-linear least squares parameter estimation against observational data",
            domain="experimental_physics",
            implementation_backend="statistical",
            formal_proof_available=False,
            symbolic_checker_available=False
        ))

    def register(self, rule: RuleDefinition) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Optional[RuleDefinition]:
        return self._rules.get(rule_id)

    def get_rule(self, rule_id: str) -> Optional[RuleDefinition]:
        return self.get(rule_id)

    def list_rules(self) -> List[RuleDefinition]:
        return list(self._rules.values())

    def list_rule_ids(self) -> List[str]:
        return list(self._rules.keys())
