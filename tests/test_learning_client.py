from pathlib import Path

import pytest

from automate.dev.learning import LearningStore, build_experience
from automate.dev.learning_client import (
    WorkerTransportError,
    build_learning_handoff,
    sync_learning_store,
)


def test_learning_handoff_is_explicitly_untrusted():
    handoff = build_learning_handoff(
        request_id="learning_12345678",
        correlation_id="cycle-1",
        source_revision="a" * 40,
        source_repo="rynahmed101-sys/automate",
        source_component="test",
        artifact_type="learning_experience",
        artifact={"experience_id": "exp_" + "b" * 32},
    )
    assert handoff["authority"] == "UNTRUSTED_LEARNING_EVIDENCE"
    assert handoff["artifact_type"] == "learning_experience"


def test_sync_ingests_only_supported_validated_artifacts(monkeypatch, tmp_path: Path):
    exp = build_experience(
        action_cycle_id="cycle-remote",
        outcome="success",
        task_kind="calculus",
        task_target="example",
        strategy_id="strategy-a",
        strategy_name="Strategy A",
        observation="remote result",
        evidence_refs=[{"id": "remote-evidence"}],
    )

    monkeypatch.setattr(
        "automate.dev.learning_client.read_learning_artifacts",
        lambda **_: [
            {
                "artifactType": "learning_experience",
                "artifact": exp,
            },
            {
                "artifactType": "not-supported",
                "artifact": {},
            },
        ],
    )

    store = LearningStore(tmp_path / "learning.db")
    try:
        result = sync_learning_store(store)
        assert result["fetched"] == 2
        assert result["ingested"] == 1
        assert result["skipped"] == 1
        assert store.get_experience(exp["experience_id"]) == exp
    finally:
        store.close()


def test_sync_ingests_mirror_research_proposal_as_candidate(monkeypatch, tmp_path: Path):
    proposal = {
        "schema_version": "mirror.research_proposal.v1",
        "authority": "UNTRUSTED_RESEARCH_PROPOSAL",
        "proposal_id": "proposal_" + "d" * 32,
        "request_id": "research_12345678",
        "capability_id": "stage.discovery",
        "source_revision": "a" * 40,
        "candidate_capability": {
            "id": "candidate.novel.method",
            "name": "Novel method",
            "summary": "A candidate method discovered by Mirror",
            "prerequisites": ["stage1b"],
            "dependencies": ["stage1b"],
        },
        "evidence_refs": ["experiment:run-1"],
        "assumptions": ["bounded input"],
        "risks": ["unverified"],
        "limitations": ["candidate only"],
        "status": "CANDIDATE",
    }
    monkeypatch.setattr(
        "automate.dev.learning_client.read_learning_artifacts",
        lambda **_: [{"artifactType": "research_proposal", "artifact": proposal}],
    )
    store = LearningStore(tmp_path / "learning.db")
    try:
        result = sync_learning_store(store)
        assert result["ingested"] == 1
        candidates = store.list_discovery_candidates()
        assert candidates[0]["proposal_id"] == proposal["proposal_id"]
        assert candidates[0]["status"] == "CANDIDATE"
    finally:
        store.close()


def test_sync_rejects_remote_adopted_lesson(monkeypatch, tmp_path: Path):
    lesson = {
        "schema_version": "automate.learning_lesson.v1",
        "lesson_id": "les_" + "e" * 32,
        "lesson_type": "strategy",
        "statement": "Remote artifact must not self-promote.",
        "scope": {"task_kind": "calculus", "task_target": "example", "strategy_id": "s"},
        "preconditions": [],
        "expected_effect": "none",
        "supporting_experience_ids": ["exp_" + "f" * 32],
        "verification_evidence": [{"id": "remote"}],
        "status": "ADOPTED",
        "provenance": {},
    }
    monkeypatch.setattr(
        "automate.dev.learning_client.read_learning_artifacts",
        lambda **_: [{"artifactType": "learning_lesson", "artifact": lesson}],
    )
    store = LearningStore(tmp_path / "learning.db")
    try:
        result = sync_learning_store(store)
        assert result["ingested"] == 0
        assert result["skipped"] == 1
        assert "promotion state" in result["errors"][0]
    finally:
        store.close()


def test_submit_learning_artifact_uses_durable_job_endpoint(monkeypatch):
    captured = {}

    def fake_request_json(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return {"success": True, "jobId": "job-learning-test"}

    monkeypatch.setattr("automate.dev.learning_client._request_json", fake_request_json)

    from automate.dev.learning_client import submit_learning_artifact

    result = submit_learning_artifact(
        {"experience_id": "exp_" + "a" * 32},
        artifact_type="learning_experience",
        request_id="learning_" + "b" * 32,
        correlation_id="cycle-test",
        source_revision="c" * 40,
        endpoint="https://worker.example",
        token="test-token",
    )

    assert result["jobId"] == "job-learning-test"
    assert captured["url"] == "https://worker.example/jobs"
    assert captured["kwargs"]["method"] == "POST"
    assert captured["kwargs"]["body"]["schema_version"] == "automate.learning_handoff.v1"
