import json
from pathlib import Path

from automate.dev.verification_self_test import main


def test_real_installed_backlog_identifies_stage1b(monkeypatch, tmp_path, capsys):
    backlog = {
        "first_frontier": {"capability_id": "stage1b.improper_integrals"},
    }
    path = tmp_path / "backlog.json"
    path.write_text(json.dumps(backlog), encoding="utf-8")

    snapshot = {
        "main_sha": "a"*40,
        "engine_sha": "b"*40,
        "requested_revision": "b"*40,
        "workflow_runs_main": [],
        "workflow_runs_engine": [],
        "pull_requests": [],
        "compare": {},
    }
    from automate.dev import verification_self_test as module
    monkeypatch.setattr(module, "live_repository_snapshot", lambda _: snapshot)

    class FakeResult:
        packet = {
            "authority": "EVIDENCE_ONLY",
            "packet_id": "pkt_" + "0"*32,
            "action_cycle_id": "cycle_" + "b"*32,
            "capability_id": "stage1b.improper_integrals",
            "repository": "rynahmed101-sys/automate",
            "exact_commit_sha": "b"*40,
            "branch": "engine",
            "evidence_state": "PARTIALLY_SUPPORTED",
            "unresolved": ["Security Audit evidence is missing"],
        }

    fake_packet = FakeResult()
    monkeypatch.setattr(
        module,
        "run_backlog_item",
        lambda **kwargs: {
            "packet": fake_packet.packet,
            "evidence_state": "PARTIALLY_SUPPORTED",
            "reconciliation": {"findings": []},
            "request": {
                "action_cycle_id": "cycle_" + "b"*32,
                "request_id": "ver_" + "1"*32,
                "capability_id": "stage1b.improper_integrals",
                "repository": "rynahmed101-sys/automate",
                "revision": "b"*40,
                "branch": "engine",
                "scope": ["mathematical"],
                "parent_ids": [],
            },
        }
    )
    monkeypatch.setattr(module, "validate_packet_consistency", lambda *a, **k: [])
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["first_frontier"]["capability_id"] == "stage1b.improper_integrals"
    assert output["evidence_state"] == "PARTIALLY_SUPPORTED"
    assert output["promotion"]["allowed"] is False
    assert output["packet_path"].startswith("data/verification-packets/")
