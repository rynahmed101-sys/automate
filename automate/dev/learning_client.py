"""Optional remote adapter for Automate's durable learning ledger.

The local LearningStore remains the canonical local cache. This adapter lets
Automate synchronize untrusted learning artifacts through Chanfana without
making network availability part of the scientific execution path.

Environment variables:
    AUTOMATE_LEARNING_ENDPOINT
    AUTOMATE_LEARNING_TOKEN
"""
from __future__ import annotations

import os
from typing import Any, Mapping
from urllib.parse import quote

from automate.dev.learning import (
    LearningError,
    LearningStore,
    validate_evolution_proposal,
    validate_experience,
    validate_lesson,
    validate_discovery_proposal,
)
from automate.dev.worker_client import WorkerTransportError, _request_json


SUPPORTED_ARTIFACTS = {
    "learning_experience",
    "learning_lesson",
    "evolution_proposal",
}


def learning_endpoint(value: str | None = None) -> str:
    endpoint = (value or os.getenv("AUTOMATE_LEARNING_ENDPOINT") or "").strip().rstrip("/")
    if not endpoint:
        raise WorkerTransportError("AUTOMATE_LEARNING_ENDPOINT is required")
    return endpoint


def learning_token(value: str | None = None) -> str:
    token = (value or os.getenv("AUTOMATE_LEARNING_TOKEN") or "").strip()
    if not token:
        raise WorkerTransportError("AUTOMATE_LEARNING_TOKEN is required")
    return token


def read_learning_artifacts(
    *,
    endpoint: str | None = None,
    token: str | None = None,
    artifact_type: str | None = None,
    source_repo: str | None = None,
    limit: int = 50,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    if not 1 <= int(limit) <= 100:
        raise WorkerTransportError("learning read limit must be between 1 and 100")
    query = [f"limit={int(limit)}"]
    if artifact_type:
        query.append("artifactType=" + quote(artifact_type, safe=""))
    if source_repo:
        query.append("sourceRepo=" + quote(source_repo, safe=""))
    result = _request_json(
        learning_endpoint(endpoint) + "/learning?" + "&".join(query),
        token=learning_token(token),
        timeout=timeout,
    )
    if result.get("success") is not True:
        raise WorkerTransportError("learning service did not return success")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list):
        raise WorkerTransportError("learning service returned an invalid artifacts list")
    return [item for item in artifacts if isinstance(item, dict)]


def build_learning_handoff(
    *,
    request_id: str,
    correlation_id: str,
    source_revision: str | None,
    source_repo: str,
    source_component: str,
    artifact_type: str,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    if artifact_type not in SUPPORTED_ARTIFACTS | {"research_proposal", "research_result", "evolution_plan"}:
        raise LearningError(f"unsupported learning handoff artifact type: {artifact_type}")
    return {
        "schema_version": "automate.learning_handoff.v1",
        "authority": "UNTRUSTED_LEARNING_EVIDENCE",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "source_revision": source_revision,
        "artifact_type": artifact_type,
        "artifact": dict(artifact),
        "provenance": {
            "source_repo": source_repo,
            "source_component": source_component,
        },
    }


def submit_learning_artifact(
    artifact: Mapping[str, Any],
    *,
    artifact_type: str,
    request_id: str,
    correlation_id: str,
    source_revision: str | None,
    source_repo: str = "rynahmed101-sys/automate",
    source_component: str = "learning",
    endpoint: str | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    handoff = build_learning_handoff(
        request_id=request_id,
        correlation_id=correlation_id,
        source_revision=source_revision,
        source_repo=source_repo,
        source_component=source_component,
        artifact_type=artifact_type,
        artifact=artifact,
    )
    return _request_json(
        learning_endpoint(endpoint) + "/jobs",
        token=learning_token(token),
        method="POST",
        body=handoff,
        timeout=timeout,
    )


def _ingest_one(store: LearningStore, item: Mapping[str, Any]) -> str:
    artifact_type = item.get("artifactType")
    artifact = item.get("artifact")
    if not isinstance(artifact, Mapping):
        raise LearningError("remote learning artifact is not an object")

    if artifact_type == "learning_experience":
        errors = validate_experience(artifact)
        if errors:
            raise LearningError("; ".join(errors))
        return store.add_experience(artifact)
    if artifact_type == "learning_lesson":
        errors = validate_lesson(artifact)
        if errors:
            raise LearningError("; ".join(errors))
        if artifact.get("status") != "CANDIDATE":
            raise LearningError(
                "remote learning lessons may be synchronized only as CANDIDATE artifacts; "
                "promotion state must be re-established through the local verification boundary"
            )
        return store.add_lesson(artifact)
    if artifact_type == "research_proposal":
        errors = validate_discovery_proposal(artifact)
        if errors:
            raise LearningError("; ".join(errors))
        return store.add_discovery_candidate(artifact)
    if artifact_type == "evolution_proposal":
        errors = validate_evolution_proposal(artifact)
        if errors:
            raise LearningError("; ".join(errors))
        if artifact.get("status") != "CANDIDATE":
            raise LearningError(
                "remote evolution proposals may be synchronized only as CANDIDATE artifacts; "
                "promotion state must be re-established through the local verification boundary"
            )
        return store.add_evolution_proposal(artifact)
    raise LearningError(f"unsupported remote artifact type: {artifact_type}")


def sync_learning_store(
    store: LearningStore,
    *,
    endpoint: str | None = None,
    token: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    artifacts = read_learning_artifacts(
        endpoint=endpoint,
        token=token,
        limit=limit,
    )
    ingested = 0
    skipped = 0
    errors: list[str] = []
    # Dependencies flow from experiences -> lessons. Ingest the dependency-bearing
    # layer first so a bounded page containing both can be reconciled deterministically.
    ordered = sorted(
        artifacts,
        key=lambda item: (
            0 if item.get("artifactType") == "learning_experience"
            else 1 if item.get("artifactType") == "research_proposal"
            else 2
        ),
    )
    for item in ordered:
        try:
            _ingest_one(store, item)
            ingested += 1
        except LearningError as exc:
            skipped += 1
            errors.append(str(exc))
    return {
        "fetched": len(artifacts),
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
    }
