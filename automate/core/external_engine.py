"""Common provenance model for bounded external verification engines."""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    runtime_identity: str = "unspecified"
    executable_path: Optional[str] = None
    executable_fingerprint_sha256: Optional[str] = None
    runtime_environment_fingerprint_sha256: Optional[str] = None
    adapter_version: str = "v1"
    provenance_schema_version: str = "v2"
    execution_status: ExternalExecutionStatus
    independence_class: ExternalIndependence
    input_fingerprint_sha256: str
    claim_fingerprint_sha256: Optional[str] = None
    comparison_method: str
    sandbox_target: str
    sandbox_limits: Dict[str, Any] = Field(default_factory=dict)
    output_fingerprint_sha256: Optional[str] = None
    comparison_target_fingerprint_sha256: Optional[str] = None
    comparison_target_source: Literal["none", "caller_supplied", "independent_renderer"] = "none"
    runtime_dependency_versions: Dict[str, str] = Field(default_factory=dict)
    provenance_fingerprint_sha256: Optional[str] = None
    checks_performed: int = 0
    error: Optional[str] = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("input_fingerprint_sha256", "claim_fingerprint_sha256", "output_fingerprint_sha256", "comparison_target_fingerprint_sha256", "provenance_fingerprint_sha256")
    @classmethod
    def validate_fingerprint(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        import re
        if re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
            raise ValueError("fingerprints must be 64-character hexadecimal SHA-256 values")
        return value

    @model_validator(mode="after")
    def bind_provenance(self) -> "ExternalEngineEvidence":
        if not self.runtime_dependency_versions:
            versions: Dict[str, str] = {}
            for package in ("automate-physics", "pydantic", "sympy", "einsteinpy"):
                try:
                    versions[package] = metadata.version(package)
                except metadata.PackageNotFoundError:
                    continue
            self.runtime_dependency_versions = dict(sorted(versions.items()))

        payload = self.model_dump(exclude={"provenance_fingerprint_sha256"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.provenance_fingerprint_sha256 = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        return self

    def to_report(self) -> Dict[str, Any]:
        return self.model_dump()
