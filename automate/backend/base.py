"""
Base interfaces and data contracts for verification backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.claim import (
    build_claim_identity,
    build_dependency_fingerprint,
    compute_evidence_fingerprint,
)


import time


class VerificationEvidence(BaseModel):
    """
    Structured machine-auditable verification evidence.
    Keeps proof/test evidence distinct from status.
    """
    backend: str
    backend_version: str
    graph_id: Optional[str] = None
    edge_id: Optional[str] = None
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
    claim_schema_version: Optional[str] = None
    claim_fingerprint_sha256: Optional[str] = None
    dependency_fingerprint_sha256: Optional[str] = None
    evidence_fingerprint_sha256: Optional[str] = None
    claim_identity: Dict[str, Any] = Field(default_factory=dict)

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
    claim_schema_version: Optional[str] = None
    claim_fingerprint_sha256: Optional[str] = None
    dependency_fingerprint_sha256: Optional[str] = None
    evidence_fingerprint_sha256: Optional[str] = None
    claim_identity: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseChecker(ABC):
    """
    Abstract interface for verification backends.

    Subclasses are automatically wrapped so every backend report receives the
    same canonical claim/dependency/evidence identity metadata. The mathematical
    claim is not compared to any external theory here.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        verify = cls.__dict__.get("verify_edge")
        if verify is None or getattr(verify, "_automate_claim_stamped", False):
            return

        from functools import wraps

        @wraps(verify)
        def _claim_stamped_verify(self, edge, graph):
            report = verify(self, edge, graph)
            if isinstance(report, VerificationReport):
                return self._stamp_report(report, edge, graph)
            return report

        _claim_stamped_verify._automate_claim_stamped = True
        cls.verify_edge = _claim_stamped_verify

    @staticmethod
    def _stamp_report(report: VerificationReport, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        identity = build_claim_identity(graph, edge)
        dependency_hash = build_dependency_fingerprint(graph, edge)
        evidence_hash = compute_evidence_fingerprint(report.to_dict())
        identity_dict = identity.model_dump()

        report.claim_schema_version = identity.schema_version
        report.claim_fingerprint_sha256 = identity.claim_fingerprint_sha256
        report.dependency_fingerprint_sha256 = dependency_hash
        report.evidence_fingerprint_sha256 = evidence_hash
        report.claim_identity = identity_dict
        report.details = dict(report.details)
        report.details.update({
            "claim_schema_version": identity.schema_version,
            "claim_fingerprint_sha256": identity.claim_fingerprint_sha256,
            "dependency_fingerprint_sha256": dependency_hash,
            "evidence_fingerprint_sha256": evidence_hash,
            "claim_identity": identity_dict,
        })

        if report.evidence is not None:
            report.evidence.claim_schema_version = identity.schema_version
            report.evidence.claim_fingerprint_sha256 = identity.claim_fingerprint_sha256
            report.evidence.dependency_fingerprint_sha256 = dependency_hash
            report.evidence.evidence_fingerprint_sha256 = evidence_hash
            report.evidence.claim_identity = identity_dict

        return report

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
