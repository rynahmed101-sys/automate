"""Tests for controlled application of worker proposals."""

import hashlib

import pytest

from automate.dev.apply import apply_worker_result
from automate.dev.inventory import InventoryError


def git_blob_sha(content: str) -> str:
    raw = content.encode("utf-8")
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def packet():
    return {
        "request_id": "wrk_test_12345678",
        "constraints": {
            "allowed_path_prefixes": ["automate/backend", "tests"],
            "forbidden_paths": ["docs/PROJECT_PHASE_LEDGER.md"],
            "max_files": 5,
        },
    }


def test_apply_worker_update(tmp_path):
    target = tmp_path / "automate/backend/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")

    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "proposed",
        "changes": [
            {
                "operation": "update",
                "path": "automate/backend/example.py",
                "expected_sha": git_blob_sha("old\n"),
                "content": "new\n",
            }
        ],
        "tests": [],
        "unresolved": [],
    }

    changed = apply_worker_result(packet(), result, root=tmp_path)
    assert changed == ["automate/backend/example.py"]
    assert target.read_text(encoding="utf-8") == "new\n"


def test_apply_worker_rejects_stale_update(tmp_path):
    target = tmp_path / "automate/backend/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("current\n", encoding="utf-8")
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "proposed",
        "changes": [
            {
                "operation": "update",
                "path": "automate/backend/example.py",
                "expected_sha": git_blob_sha("stale\n"),
                "content": "new\n",
            }
        ],
        "tests": [],
        "unresolved": [],
    }
    with pytest.raises(InventoryError, match="stale"):
        apply_worker_result(packet(), result, root=tmp_path)


def test_apply_worker_rejects_path_traversal(tmp_path):
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "proposed",
        "changes": [
            {
                "operation": "create",
                "path": "../escape.py",
                "expected_sha": None,
                "content": "bad\n",
            }
        ],
        "tests": [],
        "unresolved": [],
    }
    with pytest.raises(InventoryError):
        apply_worker_result(packet(), result, root=tmp_path)


def test_apply_worker_rejects_non_proposed_status(tmp_path):
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "submitted",
        "changes": [],
        "tests": [],
        "unresolved": [],
    }
    with pytest.raises(InventoryError, match="only a 'proposed'"):
        apply_worker_result(packet(), result, root=tmp_path)
