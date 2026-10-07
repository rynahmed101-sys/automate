from click.testing import CliRunner
from automate.dev.cli import capability


def test_automatic_readiness_reports_hold_without_cli_failure(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.readiness.auto_readiness",
        lambda repository: {
            "ready": False,
            "bootstrap_ready": True,
            "blocking_gates": ["github_lifecycle_exercised"],
        },
    )
    result = CliRunner().invoke(capability, ["autonomous-readiness", "--auto", "--json"])
    assert result.exit_code == 0
    assert '"ready": false' in result.output


def test_manual_readiness_still_fails_when_not_ready():
    result = CliRunner().invoke(capability, ["autonomous-readiness", "--json"])
    assert result.exit_code == 1
