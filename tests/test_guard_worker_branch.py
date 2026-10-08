from automate.dev.guard import validate_branch_scope


def test_known_worker_generated_capability_branch_is_allowed(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.guard.load_inventory",
        lambda: {
            "capabilities": [
                {"id": "stage1b.series_expansions", "implementation_state": "planned", "references": []},
            ],
            "branch_policy": {"shared_integration_files": []},
        },
    )
    assert validate_branch_scope(
        "feat/stage1b.series_expansions-20261008",
        ["automate/backend/sympy_backend.py"],
    ) == []


def test_unknown_worker_generated_capability_branch_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.guard.load_inventory",
        lambda: {
            "capabilities": [
                {"id": "stage1b.series_expansions", "implementation_state": "planned", "references": []},
            ],
            "branch_policy": {"shared_integration_files": []},
        },
    )
    errors = validate_branch_scope(
        "feat/not_a_known_capability-20261008",
        ["automate/backend/sympy_backend.py"],
    )
    assert errors
