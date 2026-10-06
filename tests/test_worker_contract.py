"""Tests for the autonomous worker contract foundation."""

from pathlib import Path

import pytest

from automate.dev.worker import build_worker_packet, validate_worker_result


def test_worker_packet_for_current_frontier_is_bounded():
    packet = build_worker_packet("stage1b.improper_integrals")
    body = packet["packet"]
    assert packet["schema_version"] == "automate.worker.v1"
    assert body["task"]["source"] == "github_issue"
    assert body["task"]["ref"] == "115"
    assert "Fail closed when symbolic convergence cannot be established." in body["task"]["requirements"]
    assert body["capability"]["id"] == "stage1b.improper_integrals"
    assert body["repository"]["base_branch"] == "main"
    assert body["constraints"]["allow_delete"] is False
    assert "docs/PROJECT_PHASE_LEDGER.md" in body["constraints"]["forbidden_paths"]
    assert body["verification"]["test_targets"] == ["tests/test_improper_integrals.py"]
    assert body["constraints"]["allowed_path_prefixes"] == [
        "automate/backend/improper_integrals_backend.py",
        "tests/test_improper_integrals.py",
        "docs/capabilities/improper_integrals.md",
    ]


def test_worker_packet_rejects_unready_capability():
    with pytest.raises(Exception):
        build_worker_packet("stage1c.ode")


def test_worker_packet_rejects_capability_without_canonical_scope():
    with pytest.raises(Exception):
        build_worker_packet("stage1b.fundamental_theorem")


def test_worker_result_rejects_out_of_scope_change():
    packet = build_worker_packet("stage1b.improper_integrals")["packet"]
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": packet["request_id"],
        "status": "proposed",
        "changes": [{"operation": "update", "path": "automate/dev/inventory.py", "expected_sha": "0000000000000000000000000000000000000000", "content": "bad"}],
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
        "changes": [{"operation": "update", "path": "docs/PROJECT_PHASE_LEDGER.md", "expected_sha": "0000000000000000000000000000000000000000", "content": "bad"}],
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
    assert any("not one of" in error for error in errors)


def test_worker_result_schema_file_exists():
    assert Path("schemas/automate-worker-result-v1.json").exists()


def test_worker_result_rejects_descendant_of_canonical_file():
    from automate.dev.worker import validate_worker_result

    packet = {
        "request_id": "wrk_test_12345678",
        "constraints": {
            "allowed_path_prefixes": ["automate/backend/example.py"],
            "forbidden_paths": [],
            "max_files": 5,
        },
    }
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "proposed",
        "changes": [
            {
                "operation": "create",
                "path": "automate/backend/example.py/extra.py",
                "expected_sha": None,
                "content": "bad\n",
            }
        ],
        "tests": [],
        "unresolved": [],
    }
    errors = validate_worker_result(result, packet)
    assert any("outside allowed capability paths" in error for error in errors)


def test_worker_packet_preserves_explicit_context():
    from automate.dev.worker import build_worker_packet

    packet = build_worker_packet(
        "stage1b.improper_integrals",
        context_files=[{
            "path": "tests/test_improper_integrals.py",
            "sha": "0" * 40,
            "content": "explicit context",
        }],
    )
    paths = [item["path"] for item in packet["packet"]["context"]["files"]]
    assert "tests/test_improper_integrals.py" in paths
    assert packet["packet"]["context"]["files"][0]["content"] == "explicit context"
