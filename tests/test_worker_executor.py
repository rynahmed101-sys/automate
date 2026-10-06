"""Tests for the isolated worker executor."""

import sys
from pathlib import Path
from unittest.mock import patch

from automate.dev.executor import run_approved_tests


def test_executor_uses_packet_test_targets(tmp_path: Path):
    target = tmp_path / "tests/test_example.py"
    target.parent.mkdir(parents=True)
    target.write_text("def test_example():\n    assert True\n", encoding="utf-8")
    packet = {"verification": {"test_targets": ["tests/test_example.py"]}}
    with patch("automate.dev.executor.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "ok"
        run.return_value.stderr = ""
        result = run_approved_tests(packet, root=tmp_path)
    assert result["status"] == "passed"
    run.assert_called_once()
    args = run.call_args.args[0]
    assert args[:4] == [sys.executable, "-m", "pytest", "-q"]
    assert args[4:] == ["tests/test_example.py"]


def test_executor_never_accepts_non_test_target(tmp_path: Path):
    packet = {"verification": {"test_targets": ["rm -rf /"]}}
    try:
        run_approved_tests(packet, root=tmp_path)
    except Exception as exc:
        assert "authoritative test targets" in str(exc)
    else:
        raise AssertionError("unsafe test target was accepted")


def test_executor_rejects_path_traversal_test_target(tmp_path):
    from automate.dev.executor import WorkerExecutionError, run_approved_tests
    packet = {"verification": {"test_targets": ["tests/../escape.py"]}}
    try:
        run_approved_tests(packet, root=tmp_path)
    except WorkerExecutionError as exc:
        assert "unsafe authoritative test target" in str(exc)
    else:
        raise AssertionError("unsafe test target was accepted")


def test_executor_requires_real_test_file(tmp_path):
    from automate.dev.executor import WorkerExecutionError, run_approved_tests
    packet = {"verification": {"test_targets": ["tests/missing.py"]}}
    try:
        run_approved_tests(packet, root=tmp_path)
    except WorkerExecutionError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("missing test file was accepted")
