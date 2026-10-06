"""Tests for the bounded autonomous cycle coordinator."""

from pathlib import Path
from unittest.mock import patch

from automate.dev.autonomous import run_autonomous_cycle


def decision():
    return {
        "can_dispatch": True,
        "worker_packet": {
            "packet": {
                "request_id": "wrk_test_12345678",
                "repository": {
                    "full_name": "rynahmed101-sys/automate",
                    "base_branch": "main",
                    "base_sha_claim": "0000000000000000000000000000000000000000",
                },
                "capability": {
                    "id": "stage1b.improper_integrals",
                    "name": "Improper integrals",
                },
                "constraints": {
                    "allowed_path_prefixes": ["automate/backend"],
                    "forbidden_paths": [],
                    "branch_prefix": "feat/",
                    "max_files": 5,
                    "allow_delete": False,
                },
                "verification": {
                    "must_run_tests": True,
                    "must_report_unresolved": True,
                    "must_not_claim_certification": True,
                    "test_targets": ["tests/test_improper_integrals.py"],
                },
            }
        },
    }


def test_cycle_stops_before_dispatch_when_supervisor_blocks():
    blocked = {"can_dispatch": False, "action": "stop", "errors": ["dirty"]}
    with patch("automate.dev.autonomous.supervisor_snapshot", return_value=blocked), patch(
        "automate.dev.autonomous.dispatch_worker"
    ) as dispatch:
        result = run_autonomous_cycle("x")
    assert result["status"] == "stopped"
    dispatch.assert_not_called()


def test_cycle_can_queue_without_executing():
    with patch.dict("os.environ", {"MIRROR_RESEARCH_ENDPOINT": "https://mirror/research/world"}), patch("automate.dev.autonomous.supervisor_snapshot", return_value=decision()), patch(
        "automate.dev.autonomous.dispatch_worker",
        return_value={"queued": {"success": True, "jobId": "j1"}, "execution_requested": False},
    ) as dispatch:
        result = run_autonomous_cycle("x", worker_url="https://worker", worker_token="secret")
    assert result["status"] == "research_dispatched"
    dispatch.assert_called_once()
    assert dispatch.call_args.args[0]["schema_version"] == "mirror.research_job.v1"


def test_cycle_validates_worker_result_before_local_apply():
    result = {
        "schema_version": "automate.worker_result.v1",
        "request_id": "wrk_test_12345678",
        "status": "proposed",
        "changes": [],
        "tests": [],
        "unresolved": [],
    }
    with patch.dict("os.environ", {"MIRROR_RESEARCH_ENDPOINT": "https://mirror/research/world"}), patch(
        "automate.dev.autonomous.supervisor_snapshot", return_value=decision()), patch(
        "automate.dev.autonomous.dispatch_worker",
        side_effect=[
            {"execution": {"success": True, "result": {"schema_version": "mirror.research_result.v1", "authority": "UNTRUSTED_EXTERNAL_EVIDENCE", "results": []}}},
            {"execution": {"success": True, "result": result}},
        ],
    ), patch("automate.dev.autonomous.build_worker_commit") as commit:
        outcome = run_autonomous_cycle(
            "x",
            worker_url="https://worker",
            worker_token="secret",
            execute_worker=True,
        )
    assert outcome["status"] == "validated_proposal"
    commit.assert_not_called()
