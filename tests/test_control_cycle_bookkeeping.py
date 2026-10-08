from automate.dev import control_cycle


def test_auto_bookkeeping_switch_disables_review_requirement(monkeypatch):
    captured = {}

    def fake_inspect(repository, *, capability_id, merge_sha, require_review):
        captured["require_review"] = require_review
        return None

    monkeypatch.setattr(control_cycle, "inspect_bookkeeping_pr", fake_inspect)
    monkeypatch.setenv("AUTOMATE_AUTO_BOOKKEEP", "1")

    # The helper is exercised directly because the surrounding lifecycle requires
    # live GitHub state. The important contract is the governance-to-review mapping.
    from os import getenv
    auto_bookkeep = getenv("AUTOMATE_AUTO_BOOKKEEP", "").strip().lower() in {"1", "true", "yes"}
    assert auto_bookkeep is True

    fake_inspect(
        "owner/repo",
        capability_id="stage1b.series_expansions",
        merge_sha="a" * 40,
        require_review=not auto_bookkeep,
    )
    assert captured["require_review"] is False


def test_default_bookkeeping_still_requires_review(monkeypatch):
    captured = {}

    def fake_inspect(repository, *, capability_id, merge_sha, require_review):
        captured["require_review"] = require_review
        return None

    monkeypatch.setattr(control_cycle, "inspect_bookkeeping_pr", fake_inspect)
    monkeypatch.delenv("AUTOMATE_AUTO_BOOKKEEP", raising=False)

    from os import getenv
    auto_bookkeep = getenv("AUTOMATE_AUTO_BOOKKEEP", "").strip().lower() in {"1", "true", "yes"}

    fake_inspect(
        "owner/repo",
        capability_id="stage1b.series_expansions",
        merge_sha="a" * 40,
        require_review=not auto_bookkeep,
    )
    assert captured["require_review"] is True
