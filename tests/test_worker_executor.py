"""Tests for the isolated worker executor."""

from pathlib import Path
from unittest.mock import patch

from automate.dev.executor import run_approved_tests


def test_executor_uses_packet_test_targets(tmp_path: Path):
    packet = {
        "verification": {"test_targets": ["tests/test_example.py"]},
    }
    with patch("automate.dev.executor.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "ok"
        run.return_value.stderr = ""
        result = run_approved_tests(packet, root=tmp_path)
    assert result["status"] == "passed"
    run.assert_called_once()
    args = run.call_args.args[0]
    assert args[:4] == ["python", "-m", "pytest", "-q"]
    assert args[4:] == ["tests/test_example.py"]


def test_executor_never_accepts_non_test_target(tmp_path: Path):
    packet = {"verification": {"test_targets": ["rm -rf /"]}}
    try:
        run_approved_tests(packet, root=tmp_path)
    except Exception as exc:
        assert "authoritative test targets" in str(exc)
    else:
        raise AssertionError("unsafe test target was accepted")
