from types import SimpleNamespace

import automate.dev.bookkeeping_pr as bookkeeping


def _completed(payload):
    import json
    return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")


def test_bookkeeping_promotion_dry_run_is_race_checked(monkeypatch):
    responses = iter([
        _completed({"object": {"sha": "a" * 40}}),
        _completed({
            "state": "open",
            "base": {"ref": "main", "sha": "a" * 40},
            "head": {"sha": "b" * 40},
            "mergeable": True,
        }),
        _completed({"object": {"sha": "a" * 40}}),
    ])
    monkeypatch.setattr(bookkeeping, "_run", lambda *args, **kwargs: next(responses))

    result = bookkeeping.execute_bookkeeping_promotion(
        "owner/repo",
        42,
        current_main_sha="a" * 40,
        execute=False,
    )

    assert result["state"] == "READY_TO_MERGE"
    assert result["execution"] == "dry_run_ready"
    assert result["head_sha"] == "b" * 40


def test_bookkeeping_promotion_blocks_without_governance(monkeypatch):
    responses = iter([
        _completed({"object": {"sha": "a" * 40}}),
        _completed({
            "state": "open",
            "base": {"ref": "main", "sha": "a" * 40},
            "head": {"sha": "b" * 40},
            "mergeable": True,
        }),
        _completed({"object": {"sha": "a" * 40}}),
    ])
    monkeypatch.setattr(bookkeeping, "_run", lambda *args, **kwargs: next(responses))
    monkeypatch.delenv("AUTOMATE_AUTO_BOOKKEEP", raising=False)

    result = bookkeeping.execute_bookkeeping_promotion(
        "owner/repo",
        42,
        current_main_sha="a" * 40,
        execute=True,
    )

    assert result["state"] == "READY_TO_MERGE"
    assert result["execution"] == "blocked_by_governance"


def test_bookkeeping_promotion_blocks_when_main_moves(monkeypatch):
    monkeypatch.setattr(
        bookkeeping,
        "_run",
        lambda *args, **kwargs: _completed({"object": {"sha": "c" * 40}}),
    )

    result = bookkeeping.execute_bookkeeping_promotion(
        "owner/repo",
        42,
        current_main_sha="a" * 40,
        execute=True,
    )

    assert result["state"] == "BLOCKED_BY_RACE"
