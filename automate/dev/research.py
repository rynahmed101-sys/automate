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


def build_mirror_mission_job(
    *,
    capability: dict[str, Any],
    source_revision: str,
    request_id: str,
    correlation_id: str,
    deadline_ms: int = 300_000,
    max_response_bytes: int = 1_500_000,
) -> dict[str, Any]:
    """Commission the non-deployed Mirror lab through Chanfana durable transport."""
    if not source_revision or len(source_revision) != 40:
        raise ValueError("source_revision must be an exact Git SHA")
    objective = str(capability.get("name") or capability.get("id") or "").strip()
    task = dict(capability.get("task") or {})
    if not objective:
        raise ValueError("capability objective is required")
    mission = {
        "objective": objective,
        "capability_id": str(capability.get("id") or ""),
        "automate_revision": source_revision,
        "task": task,
        "arguments": {
            "research_world": {
                "query": (objective + (": " + str(task.get("summary") or "") if task.get("summary") else ""))[:500],
                "providers": ["crossref", "openalex", "arxiv", "github", "huggingface"],
                "limit": 5,
            }
        },
    }
    return {
        "schema_version": "mirror.mission_job.v1",
        "request_id": request_id,
        "execution_kind": "mirror_autonomous_mission",
        "target": {
            "repository": "rynahmed101-sys/the-mirror",
            "workflow": "autonomous-mission.yml",
            "ref": "main",
        },
        "mission": mission,
        "source_revision": source_revision,
        "limits": {
            "deadline_ms": deadline_ms,
            "max_response_bytes": max_response_bytes,
        },
        "provenance": {
            "capability_id": str(capability.get("id") or ""),
            "correlation_id": correlation_id,
            "requested_by": "automate",
        },
    }
