"""Tests for the bounded worker HTTP client."""

from unittest.mock import patch

import pytest

from automate.dev.worker_client import WorkerTransportError, dispatch_worker, worker_base_url, worker_token


def test_worker_configuration_requires_endpoint_and_token(monkeypatch):
    monkeypatch.delenv("AUTOMATE_WORKER_URL", raising=False)
    monkeypatch.delenv("AUTOMATE_WORKER_TOKEN", raising=False)
    with pytest.raises(WorkerTransportError):
        worker_base_url()
    with pytest.raises(WorkerTransportError):
        worker_token()


def test_dispatch_queues_without_execution():
    packet = {"schema_version": "automate.worker.v1", "packet": {"request_id": "wrk_test_12345678"}}
    with patch(
        "automate.dev.worker_client.submit_worker_packet",
        return_value={"jobId": "job-1", "state": "queued"},
    ) as submit, patch(
        "automate.dev.worker_client.start_worker_job"
    ) as execute:
        result = dispatch_worker(packet, url="https://worker.example", token="secret", execute=False)
    assert result["queued"]["jobId"] == "job-1"
    assert result["execution_requested"] is False
    submit.assert_called_once()
    execute.assert_not_called()


def test_dispatch_execution_requires_job_id():
    packet = {"schema_version": "automate.worker.v1", "packet": {"request_id": "wrk_test_12345678"}}
    with patch(
        "automate.dev.worker_client.submit_worker_packet",
        return_value={"state": "queued"},
    ):
        with pytest.raises(WorkerTransportError):
            dispatch_worker(packet, url="https://worker.example", token="secret", execute=True)


def test_dispatch_execution_calls_worker_once():
    packet = {"schema_version": "automate.worker.v1", "packet": {"request_id": "wrk_test_12345678"}}
    with patch(
        "automate.dev.worker_client.submit_worker_packet",
        return_value={"jobId": "job-1", "state": "queued"},
    ), patch(
        "automate.dev.worker_client.start_worker_job",
        return_value={"success": True, "state": "running"},
    ) as execute:
        result = dispatch_worker(packet, url="https://worker.example", token="secret", execute=True)
    assert result["execution"]["state"] == "running"
    execute.assert_called_once_with(
        "job-1",
        url="https://worker.example",
        token="secret",
        timeout=30.0,
    )
