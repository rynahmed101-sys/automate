from pathlib import Path

import pytest

from automate.dev.frontier_result import (
    FrontierProposalError,
    build_frontier_commit,
    validate_frontier_result,
)


def _result(diff="", *, status="NO_CHANGE_PROPOSED") -> dict:
    return {
        "schema_version": "mirror.frontier_result.v1",
        "authority": "UNTRUSTED_MIRROR_PROPOSAL",
        "capability_id": "stage1b.test",
        "base_revision": "a" * 40,
        "status": status,
        "proposal": {"diff": {"stdout": diff}},
    }


def _packet() -> dict:
    return {
        "repository": {"base_sha_claim": "a" * 40},
        "capability": {"id": "stage1b.test", "name": "Test capability"},
        "constraints": {
            "allowed_path_prefixes": ["automate/backend"],
            "forbidden_paths": ["docs/PROJECT_PHASE_LEDGER.md"],
            "max_files": 20,
        },
        "verification": {
            "test_targets": ["tests/test_frontier_result.py"],
        },
    }


def test_frontier_result_requires_exact_base():
    errors = validate_frontier_result(
        _result(),
        capability_id="stage1b.test",
        base_sha="b" * 40,
    )
    assert "frontier result base revision mismatch" in errors


def test_empty_frontier_diff_is_not_promoted(tmp_path: Path):
    result = build_frontier_commit(
        _result(),
        packet=_packet(),
        repository_root=tmp_path,
    )
    assert result["status"] == "no_changes"


def test_invalid_frontier_result_fails_closed(tmp_path: Path):
    with pytest.raises(FrontierProposalError):
        build_frontier_commit(
            {},
            packet=_packet(),
            repository_root=tmp_path,
        )


def test_failed_frontier_result_is_not_application_safe():
    errors = validate_frontier_result(
        _result("diff --git a/x b/x\n", status="TEST_FAILED"),
        capability_id="stage1b.test",
        base_sha="a" * 40,
    )
    assert any("not eligible for application" in error for error in errors)


def test_frontier_result_requires_diff_stdout_text():
    result = _result("x")
    result["proposal"]["diff"]["stdout"] = {"not": "text"}
    errors = validate_frontier_result(
        result,
        capability_id="stage1b.test",
        base_sha="a" * 40,
    )
    assert "frontier result diff stdout must be text" in errors
