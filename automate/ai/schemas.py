"""
Pydantic schemas for versioned AI proposals, mathematical context, and origins.
Strictly provider-neutral and machine-auditable.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ProposalOrigin(BaseModel):
    """
    Provenance of a proposal without exposing any private credentials.
    """
    type: Literal["ai", "human", "algorithm"] = "ai"
    provider: str = Field(default="unknown", description="Provider name: mock, openai, local, etc.")
    model: str = Field(default="unknown", description="Model name or architecture")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_hash: Optional[str] = None
    proposal_hash: Optional[str] = None


class CandidateNode(BaseModel):
    """
    A proposed node to be added to the derivation graph upon verification.
    """
    id: str = Field(..., description="Proposed node ID, e.g. 'node_analytic_sol'")
    expression: str = Field(..., description="Mathematical expression string")
    node_kind: str = Field(default="equation", description="expression, equation, proposition, etc.")
    dimension: str = Field(default="", description="Expected physical dimension")
    latex: Optional[str] = None
    domain: str = "general_physics"
    source: str = "ai_proposed"


class DerivationProposal(BaseModel):
    """
    Structured mathematical transformation proposed by an AI agent or researcher.
    Schema version: automate.proposal.v1
    """
    schema_version: str = "automate.proposal.v1"
    proposal_id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    proposal_type: Literal["derivation", "conjecture", "counterexample", "assumption"] = "derivation"
    input_nodes: List[str] = Field(default_factory=list, description="IDs of existing nodes used as input")
    output_nodes: List[CandidateNode] = Field(default_factory=list, description="Proposed derived nodes")
    rule: str = Field(..., description="Proposed transformation rule from RuleRegistry")
    justification: str = Field(..., description="Mathematical justification or principle")
    proposed_assumptions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Explicit new assumptions required, e.g. non-zero mass or differentiability"
    )
    side_conditions: List[str] = Field(
        default_factory=list,
        description="IDs of assumptions required to be active"
    )
    target_checker: str = Field(default="sympy", description="sympy, lean4, numerical, statistical, dimension")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    origin: ProposalOrigin = Field(default_factory=ProposalOrigin)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AIContext(BaseModel):
    """
    Controlled mathematical context exposed to AI agents.
    Excludes sensitive environment secrets, API keys, and machine paths.
    Schema version: automate.context.v1
    """
    schema_version: str = "automate.context.v1"
    theory_id: str
    theory_name: str
    description: str = ""
    domain: str = "general_physics"
    definitions: List[Dict[str, Any]] = Field(default_factory=list)
    equations: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    open_obligations: List[Dict[str, Any]] = Field(default_factory=list)
    verified_edges: List[str] = Field(default_factory=list)
    failed_edges: List[str] = Field(default_factory=list)
    available_rules: List[Dict[str, Any]] = Field(default_factory=list)
    graph_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
