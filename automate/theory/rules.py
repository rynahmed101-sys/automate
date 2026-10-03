"""
Registry of transformation rules in mathematical physics.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleDefinition(BaseModel):
    name: str = Field(..., description="Unique rule identifier")
    description: str = Field(..., description="Mathematical explanation")
    domain: str = Field(default="general_physics")
    required_assumptions: List[str] = Field(default_factory=list)
    default_checker: str = Field(default="sympy")
    citation: Optional[str] = None


class RuleRegistry:
    def __init__(self):
        self._rules: Dict[str, RuleDefinition] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        self.register(RuleDefinition(
            name="euler_lagrange",
            description="Derives equations of motion from action principle: d/dt(dL/dq_dot) - dL/dq = 0",
            domain="classical_mechanics",
            required_assumptions=["smooth_trajectories", "fixed_endpoints"],
            default_checker="sympy",
            citation="Hamilton's Principle / Variational Calculus"
        ))
        self.register(RuleDefinition(
            name="conserve_energy",
            description="Derives first integral of motion / Jacobi energy function E = sum(p_i q_dot_i) - L",
            domain="classical_mechanics",
            required_assumptions=["time_translation_invariance"],
            default_checker="lean4",
            citation="Noether's Theorem / Energy Conservation"
        ))
        self.register(RuleDefinition(
            name="solve_harmonic_oscillator",
            description="General analytical solution of linear 2nd-order ODE: x(t) = A*cos(omega*t + phi)",
            domain="classical_mechanics",
            required_assumptions=["asm_pos_mass", "asm_pos_k"],
            default_checker="sympy",
            citation="Linear Ordinary Differential Equations"
        ))
        self.register(RuleDefinition(
            name="algebraic_identity",
            description="Symbolic simplification, expansion, or algebraic equality",
            domain="mathematics",
            default_checker="sympy"
        ))
        self.register(RuleDefinition(
            name="numerical_simulation",
            description="Numerical integration of equations of motion using Runge-Kutta ODE solver",
            domain="computational_physics",
            default_checker="numerical"
        ))
        self.register(RuleDefinition(
            name="empirical_inference",
            description="Non-linear least squares parameter estimation against observational data",
            domain="experimental_physics",
            default_checker="statistical"
        ))

    def register(self, rule: RuleDefinition) -> None:
        self._rules[rule.name] = rule

    def get(self, rule_name: str) -> Optional[RuleDefinition]:
        return self._rules.get(rule_name)

    def list_rules(self) -> List[RuleDefinition]:
        return list(self._rules.values())
