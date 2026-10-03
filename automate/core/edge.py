"""
DerivationEdge: A directed transformation step between nodes in the derivation graph.
Contains machine-readable metadata, justification, checker, status, and certificate.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from automate.core.status import VerificationStatus


class DerivationCertificate(BaseModel):
    """
    Verification certificate recording low-level intermediate steps,
    formal proof terms, numerical errors, or symbolic reduction traces.
    Enables lossless mathematical compression.
    """
    rule_name: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    proof_code: Optional[str] = None  # e.g. Lean 4 theorem script
    backend_version: Optional[str] = None
    execution_time_ms: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)  # tolerances, residuals, chi2
    diagnostics: List[str] = Field(default_factory=list)


class DerivationEdge(BaseModel):
    """
    A transformation step in the derivation graph.
    """
    id: str = Field(..., description="Unique edge identifier, e.g. 'edge_euler_lagrange'")
    input_nodes: List[str] = Field(..., description="IDs of input nodes")
    output_nodes: List[str] = Field(..., description="IDs of output nodes")
    transformation_rule: str = Field(
        ...,
        description="Name of rule applied, e.g. 'euler_lagrange_equation', 'substitute', 'differentiate'"
    )
    justification: str = Field(
        ...,
        description="Mathematical justification, theorem citation, or principle"
    )
    checker: str = Field(
        default="unverified",
        description="Checker backend used: 'sympy', 'lean4', 'numerical', 'statistical', 'dimension'"
    )
    status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification status"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the transformation rule (e.g. coordinates: ['x'])"
    )
    certificate: Optional[DerivationCertificate] = Field(
        default=None,
        description="Lossless certificate storing intermediate sub-steps or formal proof code"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
