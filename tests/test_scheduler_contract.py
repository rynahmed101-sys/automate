def test_scheduler_workflow_is_disabled_by_default_and_single_flight():
    from pathlib import Path

    workflow = Path(".github/workflows/autonomous-control-cycle.yml").read_text(encoding="utf-8")
    assert "vars.AUTOMATE_CONTROL_CYCLE_ENABLED == '1'" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "AUTOMATE_AUTO_PROMOTE" in workflow
