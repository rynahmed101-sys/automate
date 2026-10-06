"""HTTP client for the bounded Automate worker API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class WorkerTransportError(RuntimeError):
    """Raised when the worker API cannot be reached or rejects a request."""


def _request_json(
    url: str,
    *,
    token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    payload = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise WorkerTransportError(f"worker request failed: {exc}") from exc

    try:
        result = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise WorkerTransportError("worker returned invalid JSON") from exc

    if not isinstance(result, dict):
        raise WorkerTransportError("worker returned a non-object JSON response")
    return result


def worker_base_url(url: str | None = None) -> str:
    value = (url or os.getenv("AUTOMATE_WORKER_URL") or "").strip().rstrip("/")
    if not value:
        raise WorkerTransportError("AUTOMATE_WORKER_URL is required")
    return value


def worker_token(token: str | None = None) -> str:
    value = (token or os.getenv("AUTOMATE_WORKER_TOKEN") or "").strip()
    if not value:
        raise WorkerTransportError("AUTOMATE_WORKER_TOKEN is required")
    return value


def submit_worker_packet(
    packet: dict[str, Any],
    *,
    url: str | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _request_json(
        worker_base_url(url) + "/jobs",
        token=worker_token(token),
        method="POST",
        body=packet,
        timeout=timeout,
    )


def execute_worker_job(
    job_id: str,
    *,
    url: str | None = None,
    token: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    return _request_json(
        worker_base_url(url) + f"/jobs/{job_id}/execute",
        token=worker_token(token),
        method="POST",
        timeout=timeout,
    )


def read_worker_job(
    job_id: str,
    *,
    url: str | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _request_json(
        worker_base_url(url) + f"/jobs/{job_id}",
        token=worker_token(token),
        timeout=timeout,
    )


def dispatch_worker(
    packet: dict[str, Any],
    *,
    url: str | None = None,
    token: str | None = None,
    execute: bool = False,
    timeout: float = 30.0,
) -> dict[str, Any]:
    queued = submit_worker_packet(packet, url=url, token=token, timeout=timeout)
    if queued.get("success") is False:
        raise WorkerTransportError("worker rejected packet submission")
    job_id = queued.get("jobId")
    if not execute:
        return {"queued": queued, "execution_requested": False}

    if not isinstance(job_id, str) or not job_id:
        raise WorkerTransportError("worker did not return a jobId")
    result = execute_worker_job(job_id, url=url, token=token, timeout=max(timeout, 120.0))
    if result.get("success") is False:
        raise WorkerTransportError("worker execution failed")
    return {
        "queued": queued,
        "execution_requested": True,
        "execution": result,
    }
