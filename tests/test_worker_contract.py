"""Tests for the autonomous worker contract foundation."""

from pathlib import Path

import pytest

from automate.dev.worker import build_worker_packet, validate_worker_result


def test_worker_packet_for_current_frontier_is_bounded():
    packet = build_worker_packet("stage1b.improper_integrals")
    body = packet["packet"]
    assert packet["schema_version"] == "automate.worker.v1"
    assert body["capability"]["id"] == "stage1b.improper_integrals"
    assert body["repository"]["base_branch"] == "main"
    assert body["constraints"]["allow_delete"] is False
    assert "docs/PROJECT_PHASE_LEDGER.md" in body["constraints"]["forbidden_paths"]
    assert "automate/backend" in body["constraints"]["allowed_path_prefixes"]


def test_worker_packet_rejects_unready_capability():
    with pytest.raises(Exception):
        build_worker_packet("stage1c.ode")


def test_worker_result_rejects_out_of_scope_change():
    packet = build_worker_packet("stage1b.improper_integrals")["packet"]
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": packet["request_id"],
        "status": "proposed",
        "changes": [{"operation": "update", "path": "automate/dev/inventory.py", "content": "bad"}],
        "tests": [],
        "unresolved": [],
    }
    errors = validate_worker_result(result, packet)
    assert any("outside allowed capability paths" in error for error in errors)


def test_worker_result_rejects_forbidden_control_plane_path():
    packet = build_worker_packet("stage1b.improper_integrals")["packet"]
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": packet["request_id"],
        "status": "proposed",
        "changes": [{"operation": "update", "path": "docs/PROJECT_PHASE_LEDGER.md", "content": "bad"}],
        "tests": [],
        "unresolved": [],
    }
    errors = validate_worker_result(result, packet)
    assert any("forbidden control-plane path" in error for error in errors)


def test_worker_result_rejects_self_certification():
    packet = build_worker_packet("stage1b.improper_integrals")["packet"]
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": packet["request_id"],
        "status": "proposed",
        "changes": [],
        "tests": [],
        "unresolved": [],
        "claims": [{"claim": "capability is certified", "supported": True}],
    }
    errors = validate_worker_result(result, packet)
    assert any("self-certify" in error for error in errors)


def test_worker_result_rejects_invalid_status():
    packet = build_worker_packet("stage1b.improper_integrals")["packet"]
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": packet["request_id"],
        "status": "not_run",
        "changes": [],
        "tests": [],
        "unresolved": [],
    }
    errors = validate_worker_result(result, packet)
    assert any("invalid" in error for error in errors)


def test_worker_result_schema_file_exists():
    assert Path("schemas/automate-worker-result-v1.json").exists()
