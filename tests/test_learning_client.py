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
