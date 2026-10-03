"""
Base interfaces and data contracts for verification backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph


import time


class VerificationEvidence(BaseModel):
    """
    Structured machine-auditable verification evidence.
    Keeps proof/test evidence distinct from status.
    """
    backend: str
    backend_version: str
    input_node_ids: List[str] = Field(default_factory=list)
    output_node_ids: List[str] = Field(default_factory=list)
    assumptions_used: List[str] = Field(default_factory=list)
    side_conditions_checked: List[str] = Field(default_factory=list)
    generated_obligations: List[Dict[str, Any]] = Field(default_factory=list)
    command_invocation: Optional[str] = None
    passed: bool = False
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    execution_time_ms: float = 0.0
    reproducibility: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    certificate_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class VerificationReport(BaseModel):
    """
    Standardized machine-readable report returned by any verification backend.
    """
    status: VerificationStatus
    backend: str = Field(..., description="Backend name: sympy, lean4, numerical, statistical, dimension")
    backend_version: str = Field(default="", description="Version of the solver / theorem prover")
    execution_time_ms: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    proof_script: Optional[str] = None
    certificates: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Optional[VerificationEvidence] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseChecker(ABC):
    """
    Abstract interface for all verification backends.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the backend."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the underlying tool."""
        pass

    @abstractmethod
    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        """
        Verifies a single derivation step in the context of the graph.
        """
        pass
