"""Bounded HTTP boundary for the evidence-only verification engine.

This service is authority-blind. It accepts an exact-revision request, runs the
verifier, and returns evidence. It does not merge code, certify capabilities,
edit the ledger, or invoke open-ended research.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from automate.dev.verification_engine import (
    build_request,
    live_repository_snapshot,
    run_backlog_item,
    validate_packet_consistency,
)

MAX_REQUEST_BYTES = 1_000_000
MAX_RESPONSE_BYTES = 1_500_000


def _authorized(headers: Any) -> bool:
    expected = os.getenv("VERIFICATION_ENGINE_JOB_TOKEN", "").strip()
    return bool(expected) and headers.get("Authorization") == "Bearer " + expected


def verify_payload(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    required = ("action_cycle_id", "capability_id", "repository", "revision", "branch", "scope")
    missing = [key for key in required if key not in payload]
    if missing:
        return 400, {"error": "missing required verification fields", "fields": missing}

    try:
        request = build_request(
            capability_id=str(payload["capability_id"]),
            repository=str(payload["repository"]),
            revision=str(payload["revision"]),
            branch=str(payload["branch"]),
            scope=[str(x) for x in payload["scope"]],
            action_cycle_id=str(payload["action_cycle_id"]),
            parent_ids=[str(x) for x in payload.get("parent_ids", [])],
        )
        snapshot = live_repository_snapshot(request.repository)
        snapshot["requested_revision"] = request.revision
        result = run_backlog_item(
            capability_id=request.capability_id,
            repository=request.repository,
            revision=request.revision,
            branch=request.branch,
            action_cycle_id=request.action_cycle_id,
            snapshot=snapshot,
            evidence_db="data/verification-evidence.db",
        )
        consistency = validate_packet_consistency(
            result["packet"],
            request=request,
            repository_state=snapshot,
        )
        response = {
            "schema_version": "automate.verification_result.v1",
            "authority": "EVIDENCE_ONLY",
            "request_id": request.request_id,
            "action_cycle_id": request.action_cycle_id,
            "capability_id": request.capability_id,
            "source_revision": request.revision,
            "evidence_state": result["evidence_state"],
            "packet": result["packet"],
            "packet_consistency_findings": consistency,
            "reconciliation": result["reconciliation"],
            "math": result["math"],
        }
        encoded = json.dumps(response, separators=(",", ":"), default=str).encode("utf-8")
        if len(encoded) > MAX_RESPONSE_BYTES:
            return 500, {"error": "verification response exceeded bounded size"}
        return 200, response
    except (ValueError, OSError, RuntimeError) as exc:
        return 400, {"error": f"verification request failed closed: {type(exc).__name__}: {exc}"}


class VerificationHandler(BaseHTTPRequestHandler):
    server_version = "AutomateVerificationEngine/1"

    def _write(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/verification/v1/requests":
            self._write(404, {"error": "not found"})
            return
        if not _authorized(self.headers):
            self._write(403, {"error": "verification endpoint disabled or unauthorized"})
            return
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError:
            self._write(400, {"error": "Content-Length is required"})
            return
        if length < 2 or length > MAX_REQUEST_BYTES:
            self._write(413, {"error": "request exceeds bounded size"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._write(400, {"error": "malformed JSON"})
            return
        if not isinstance(payload, dict):
            self._write(400, {"error": "verification request must be a JSON object"})
            return
        status, response = verify_payload(payload)
        self._write(status, response)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), VerificationHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
