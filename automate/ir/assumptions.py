"""
First-class assumption representation and dependency tracking.
Never silently discard assumptions.
"""

from typing import Dict, Set, List, Optional, Any
from pydantic import BaseModel, Field


class Assumption(BaseModel):
    """
    An explicit mathematical or physical assumption.
    """
    id: str = Field(..., description="Unique assumption identifier, e.g. asm_m_pos")
    description: str = Field(..., description="Human-readable description")
    category: str = Field(
        default="domain_restriction",
        description="Category: positivity, nondegeneracy, boundary_condition, approximation, limit"
    )
    formal_predicate: str = Field(
        ...,
        description="Formal predicate string, e.g. 'm > 0', 'smooth(x, t)', 'boundary_term == 0'"
    )
    active: bool = Field(default=True, description="Whether this assumption is currently assumed")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AssumptionDependency(BaseModel):
    """
    Explicit dependency between declared assumptions.

    If assumption A depends on B, any claim that relies on A also inherits B.
    This records logical/precondition structure without asserting that the
    dependency itself is a theorem.
    """
    assumption_id: str = Field(..., description="Assumption whose validity depends on other assumptions")
    depends_on: List[str] = Field(default_factory=list, description="Declared prerequisite assumption IDs")
    relation: str = Field(default="requires", description="Dependency relation, e.g. 'requires' or 'derived_from'")
    justification: str = Field(default="", description="Reason this dependency is declared")
    active: bool = Field(default=True, description="Whether this dependency relation is active")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AssumptionRegistry:
    """
    Global or scoped repository of declared assumptions.
    """
    def __init__(self):
        self._assumptions: Dict[str, Assumption] = {}

    def register(self, assumption: Assumption) -> None:
        self._assumptions[assumption.id] = assumption

    def get(self, assumption_id: str) -> Optional[Assumption]:
        return self._assumptions.get(assumption_id)

    def all_assumptions(self) -> Dict[str, Assumption]:
        return dict(self._assumptions)

    def set_active(self, assumption_id: str, active: bool) -> None:
        if assumption_id in self._assumptions:
            self._assumptions[assumption_id].active = active

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._assumptions.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssumptionRegistry":
        reg = cls()
        for k, v in data.items():
            reg.register(Assumption(**v))
        return reg
