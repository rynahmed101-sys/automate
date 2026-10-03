"""
DerivationNode: A node in the derivation graph representing a mathematical expression,
its representations, domain, assumptions, and provenance.
"""

from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel, Field
from automate.ir.ast import MathematicalExpression
from automate.core.status import VerificationStatus


class DerivationNode(BaseModel):
    """
    A single node in a formal physics derivation graph.
    """
    id: str = Field(..., description="Unique node ID, e.g. 'node_lagrangian'")
    expression: MathematicalExpression = Field(..., description="Canonical IR expression")
    node_kind: str = Field(
        default="expression",
        description="Node role: 'expression', 'equation', 'proposition', 'assumption', 'observable', 'parameter', 'trajectory'"
    )
    representations: Dict[str, str] = Field(
        default_factory=dict,
        description="Alternative representations: 'latex', 'sympy', 'lean4', 'ascii'"
    )
    domain: str = Field(
        default="general_physics",
        description="Physical domain: classical_mechanics, electromagnetism, etc."
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="List of assumption IDs that this node explicitly requires"
    )
    source: str = Field(
        default="definition",
        description="Source type: 'axiom', 'definition', 'hypothesis', 'derived', 'experimental'"
    )
    status: VerificationStatus = Field(
        default=VerificationStatus.PARSED,
        description="Current verification status of this node"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_assumption(self, assumption_id: str) -> None:
        if assumption_id not in self.assumptions:
            self.assumptions.append(assumption_id)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
