"""Fail-closed research evidence contracts for autonomous workers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from jsonschema import Draft202012Validator

from automate.dev.worker import ROOT

RESEARCH_REQUEST_SCHEMA_PATH = ROOT / "schemas" / "automate-research-request-v1.json"
RESEARCH_SCHEMA_PATH = ROOT / "schemas" / "automate-research-evidence-v1.json"
MAX_SOURCE_COUNT = 50
MAX_BYTES = 50_000_000
MAX_TIMEOUT_MS = 300_000

def content_sha256(content: str | bytes) -> str:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def validate_request(request: dict[str, Any]) -> list[str]:
    schema = json.loads(RESEARCH_REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    return [error.message for error in Draft202012Validator(schema).iter_errors(request)]


def build_request(*, request_id: str, objective: str, sources: list[str],
                  max_sources: int = 10, max_bytes: int = 5_000_000,
                  timeout_ms: int = 60_000, query: str | None = None,
                  required_evidence: list[str] | None = None) -> dict[str, Any]:
    request = {
        "schema_version": "automate.research_request.v1",
        "request_id": request_id,
        "objective": objective,
        "sources": sources,
        "limits": {"max_sources": max_sources, "max_bytes": max_bytes, "timeout_ms": timeout_ms},
        "query": query,
        "required_evidence": list(required_evidence or []),
    }
    errors = validate_request(request)
    if errors:
        raise ValueError("; ".join(errors))
    return request

def validate_evidence(packet: dict[str, Any]) -> list[str]:
    schema=json.loads(RESEARCH_SCHEMA_PATH.read_text(encoding="utf-8"))
    return [error.message for error in Draft202012Validator(schema).iter_errors(packet)]

def build_evidence_packet(*, request_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    packet={"schema_version":"automate.research_evidence.v1","request_id":request_id,"sources":sources}
    errors=validate_evidence(packet)
    if errors:
        raise ValueError("; ".join(errors))
    return packet

def source_digest(source: dict[str, Any]) -> str:
    required=("source_type","locator","title","content_sha256","retrieved_at")
    missing=[key for key in required if not source.get(key)]
    if missing:
        raise ValueError("research source missing required fields: "+", ".join(missing))
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",",":")).encode()).hexdigest()


def build_mirror_research_job(
    *,
    capability: dict[str, Any],
    mirror_endpoint: str,
    request_id: str,
    correlation_id: str,
    max_results_per_provider: int = 5,
    deadline_ms: int = 120_000,
    max_response_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """Build the bounded Chanfana envelope that commissions Mirror to research a capability.

    Research is evidence acquisition, not implementation authority. The resulting packet
    deliberately names the capability frontier so the researcher can investigate mature
    implementations, counterexamples, mathematical prerequisites, and unusual alternatives.
    """
    if not mirror_endpoint:
        raise ValueError("mirror_endpoint is required")
    objective = str(capability.get("name") or capability.get("id") or "").strip()
    task = capability.get("task") or {}
    summary = str(task.get("summary") or "").strip()
    requirements = [str(x) for x in task.get("requirements", []) if str(x).strip()]
    query = objective + (": " + summary if summary else "")
    query = query[:500]
    job = {
        "schema_version": "mirror.research_job.v1",
        "request_id": request_id,
        "execution_kind": "external_research",
        "target": {"mirror_endpoint": mirror_endpoint},
        "query": query,
        "providers": ["crossref", "openalex", "arxiv", "github", "huggingface"],
        "limits": {
            "max_results_per_provider": max_results_per_provider,
            "deadline_ms": deadline_ms,
            "max_response_bytes": max_response_bytes,
        },
        "provenance": {
            "capability_id": str(capability.get("id") or ""),
            "experiment_id": None,
            "correlation_id": correlation_id,
        },
        "research_intent": {
            "objective": objective,
            "summary": summary,
            "requirements": requirements,
            "instructions": [
                "Find mature scientific and open-source approaches before recommending reinvention.",
                "Look for counterexamples, edge cases, known failure modes, and contradictory evidence.",
                "Include unusual or frontier approaches when evidence warrants them; established theory is a baseline, not a veto.",
                "Return evidence and uncertainty, not certification.",
            ],
        },
    }
    return job
