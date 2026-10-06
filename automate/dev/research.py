"""Fail-closed research evidence contracts for autonomous workers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from jsonschema import Draft202012Validator

from automate.dev.worker import ROOT

RESEARCH_SCHEMA_PATH = ROOT / "schemas" / "automate-research-evidence-v1.json"

def content_sha256(content: str | bytes) -> str:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()

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
