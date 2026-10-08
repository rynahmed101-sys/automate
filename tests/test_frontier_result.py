from pathlib import Path

import pytest

from automate.dev.frontier_result import FrontierProposalError, apply_frontier_diff, validate_frontier_result


def _result(diff="") -> dict:
    return {
        "schema_version": "mirror.frontier_result.v1",
        "authority": "UNTRUSTED_MIRROR_PROPOSAL",
        "capability_id": "stage1b.test",
        "base_revision": "a" * 40,
        "status": "NO_CHANGE_PROPOSED" if not diff else "PROPOSED",
        "proposal": {"diff": {"stdout": diff}},
    }


def test_frontier_result_requires_exact_base():
    errors = validate_frontier_result(_result(), capability_id="stage1b.test", base_sha="b" * 40)
    assert "frontier result base revision mismatch" in errors


def test_empty_frontier_diff_is_not_promoted(tmp_path: Path):
    result = apply_frontier_diff(_result(), capability_id="stage1b.test", base_sha="a" * 40, repository_root=tmp_path)
    assert result["status"] == "no_changes"


def test_invalid_frontier_result_fails_closed(tmp_path: Path):
    with pytest.raises(FrontierProposalError):
        apply_frontier_diff({}, capability_id="stage1b.test", base_sha="a" * 40, repository_root=tmp_path)


def test_failed_frontier_result_is_not_application_safe():
    result = _result("diff --git a/x b/x\n")
    result["status"] = "TEST_FAILED"
    errors = validate_frontier_result(result, capability_id="stage1b.test", base_sha="a" * 40)
    assert any("not eligible for application" in error for error in errors)


def test_frontier_result_requires_diff_stdout_text():
    result = _result("x")
    result["proposal"]["diff"]["stdout"] = {"not": "text"}
    errors = validate_frontier_result(result, capability_id="stage1b.test", base_sha="a" * 40)
    assert "frontier result diff stdout must be text" in errors
