from pathlib import Path


def test_control_cycle_configures_machine_git_identity_before_reconciliation():
    workflow = Path(".github/workflows/control-cycle.yml").read_text(encoding="utf-8")
    reconcile = workflow.split("Reconcile engine with authoritative main", 1)[1].split("      - name:", 1)[0]
    assert 'git config user.name "automate-control-plane[bot]"' in reconcile
    assert 'git config user.email "41898282+github-actions[bot]@users.noreply.github.com"' in reconcile


def test_control_cycle_does_not_require_mirror_deployment():
    workflow = Path(".github/workflows/control-cycle.yml").read_text(encoding="utf-8")
    assert "MIRROR_FRONTIER_ENDPOINT" not in workflow
    assert "MIRROR_FRONTIER_JOB_TOKEN" not in workflow
    assert "MIRROR_AUTONOMOUS_DISCOVERY_ENDPOINT" not in workflow
    assert "MIRROR_AUTONOMOUS_DISCOVERY_TOKEN" not in workflow
    assert 'AUTOMATE_MIRROR_DISCOVERY_ENABLED: "0"' in workflow


def test_authoritative_ledger_keeps_series_before_later_stage_work():
    ledger = Path("docs/PROJECT_PHASE_LEDGER.md").read_text(encoding="utf-8")
    series = ledger.index("Taylor / Maclaurin series")
    ode = ledger.index("## 1C. General ODEs")
    assert series < ode
    assert "- [x] Taylor / Maclaurin series and higher-order expansions" in ledger
