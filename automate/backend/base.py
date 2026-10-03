"""
Base interfaces and data contracts for verification backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph


class VerificationReport(BaseModel):
    """
    Standardized machine-readable report returned by any verification backend.
    """
    status: VerificationStatus
    backend: str = Field(..., description="Backend name: sympy, lean4, numerical, statistical, dimension")
    backend_version: str = Field(default="", description="Version of the solver / theorem prover")
    execution_time_ms: float = Field(default=0.0, description="Runtime in milliseconds")
    passed: bool = Field(default=False, description="True if verification succeeded")
    details: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary verification metadata")
    error_message: Optional[str] = Field(default=None, description="Diagnostic error trace if failed")
    proof_script: Optional[str] = Field(default=None, description="Formal proof or verification code used")
    certificates: List[Dict[str, Any]] = Field(default_factory=list, description="Sub-step micro-proofs")

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
