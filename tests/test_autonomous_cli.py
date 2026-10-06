from click.testing import CliRunner

from automate.cli import main


def test_autonomous_loop_cli_is_bounded_and_machine_readable(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.daemon.run_autonomous_cycle",
        lambda repository, **kwargs: {"status": "stopped", "repository": repository},
    )
    result = CliRunner().invoke(
        main,
        ["autonomous-loop", "--repository", "rynahmed101-sys/automate", "--max-cycles", "2", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert '"cycle": 1' in result.output
    assert '"cycle": 2' in result.output
