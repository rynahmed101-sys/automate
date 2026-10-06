from click.testing import CliRunner

from automate.cli import main


def test_learning_cli_snapshot_is_machine_readable(tmp_path):
    result = CliRunner().invoke(
        main,
        ["learn", "snapshot", "--db", str(tmp_path / "learning.db")],
    )
    assert result.exit_code == 0, result.output
    assert '"experience_count": 0' in result.output
    assert "strategy_selection_is_conservative" in result.output


def test_learning_cli_transition_does_not_forge_independence_marker(tmp_path):
    from automate.dev.learning import LearningStore, build_experience, build_lesson

    store = LearningStore(tmp_path / "learning.db")
    try:
        exp = build_experience(
            action_cycle_id="cycle-cli",
            outcome="success",
            task_kind="calculus",
            task_target="example",
            strategy_id="s",
            strategy_name="s",
            observation="passed",
            evidence_refs=[{"id": "run"}],
        )
        eid = store.add_experience(exp)
        lesson = build_lesson(
            lesson_type="strategy",
            statement="test lesson",
            scope={"task_kind": "calculus", "task_target": "example", "strategy_id": "s"},
            supporting_experience_ids=[eid],
        )
        store.add_lesson(lesson)
    finally:
        store.close()

    result = CliRunner().invoke(
        main,
        [
            "learn", "transition", lesson["lesson_id"], "VERIFIED",
            "--reason", "verification evidence supplied",
            "--evidence-id", "verification-1",
            "--db", str(tmp_path / "learning.db"),
        ],
    )
    assert result.exit_code == 0, result.output

    adopted = CliRunner().invoke(
        main,
        [
            "learn", "transition", lesson["lesson_id"], "ADOPTED",
            "--reason", "adoption attempt without independence marker",
            "--evidence-id", "same-run",
            "--db", str(tmp_path / "learning.db"),
        ],
    )
    assert adopted.exit_code != 0


def test_learning_cli_loop_and_triage_are_machine_readable(tmp_path):
    from pathlib import Path
    import json

    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps({
        "schema_version": "mirror.research_proposal.v1",
        "authority": "UNTRUSTED_RESEARCH_PROPOSAL",
        "proposal_id": "proposal_" + "f" * 32,
        "request_id": "research_12345678",
        "capability_id": "stage.discovery",
        "source_revision": "a" * 40,
        "candidate_capability": {
            "id": "candidate.cli.discovery",
            "name": "CLI discovery",
            "summary": "A candidate",
            "prerequisites": ["stage1a.linear_algebra"],
            "dependencies": ["stage1a.linear_algebra"],
        },
        "evidence_refs": ["run:1"],
        "assumptions": [],
        "risks": [],
        "limitations": [],
        "status": "CANDIDATE",
    }), encoding="utf-8")

    triage = CliRunner().invoke(
        main,
        ["learn", "triage-discovery", str(proposal_path)],
    )
    assert triage.exit_code == 0, triage.output
    payload = json.loads(triage.output)
    assert payload["canonical_inventory_mutated"] is False
