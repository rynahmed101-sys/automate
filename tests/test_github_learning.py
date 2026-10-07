from automate.dev.github_learning import GitHubLearningSyncError, sync_github_actions
from automate.dev.learning import LearningStore


def test_github_learning_sync_records_completed_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "automate.dev.github_learning._request_json",
        lambda *_args, **_kwargs: {
            "workflow_runs": [
                {
                    "id": 123,
                    "name": "Automate CI",
                    "run_number": 42,
                    "status": "completed",
                    "conclusion": "failure",
                    "head_sha": "a" * 40,
                },
                {
                    "id": 124,
                    "name": "Automate CI",
                    "run_number": 43,
                    "status": "in_progress",
                    "conclusion": None,
                    "head_sha": "b" * 40,
                },
            ]
        },
    )
    store = LearningStore(tmp_path / "learning.db")
    try:
        result = sync_github_actions(store, token="secret", limit=2)
        assert result["recorded"] == 1
        assert result["skipped"] == 1
        assert store.snapshot()["experience_count"] == 1
    finally:
        store.close()


def test_github_learning_sync_requires_bounded_limit(tmp_path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        import pytest
        with pytest.raises(GitHubLearningSyncError, match="between 1 and 100"):
            sync_github_actions(store, token="secret", limit=101)
    finally:
        store.close()
