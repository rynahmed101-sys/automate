"""Common provenance model for bounded external verification engines."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


ExternalExecutionStatus = Literal[
    "UNAVAILABLE", "UNSUPPORTED", "COMPLETED",
    "EXECUTION_FAILED", "MATHEMATICAL_DISCREPANCY",
]
ExternalIndependence = Literal[
    "NOT_RUN", "DIFFERENT_ENGINE", "CROSS_CHECK_FAILED", "UNVERIFIED",
]


class ExternalEngineEvidence(BaseModel):
    """Machine-readable provenance shared by external-engine adapters."""

    engine: str
    version: str
    execution_status: ExternalExecutionStatus
    independence_class: ExternalIndependence
    input_fingerprint_sha256: str
    claim_fingerprint_sha256: Optional[str] = None
    comparison_method: str
    sandbox_target: str
    sandbox_limits: Dict[str, Any] = Field(default_factory=dict)
    output_fingerprint_sha256: Optional[str] = None
    checks_performed: int = 0
    error: Optional[str] = None
    notes: list[str] = Field(default_factory=list)

    def to_report(self) -> Dict[str, Any]:
        return self.model_dump()
