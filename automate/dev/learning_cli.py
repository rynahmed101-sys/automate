"""CLI for the evidence-driven learning and self-evolution control plane."""
from __future__ import annotations

import json
from pathlib import Path

import click

from automate.dev.learning import (
    LearningError,
    LearningStore,
    admission_decision,
    build_evolution_proposal,
    build_experience,
    build_lesson,
)


@click.group(name="learn")
def learn() -> None:
    """Record experience, inspect learned strategy evidence, and manage lessons."""


def _store(db: str) -> LearningStore:
    return LearningStore(Path(db))


@learn.command("record")
@click.argument("json_file", type=click.Path(exists=True))
@click.option("--db", default="data/learning.db", show_default=True)
def record(json_file: str, db: str) -> None:
    """Validate and persist one learning experience JSON artifact."""
    store = _store(db)
    try:
        payload = json.loads(Path(json_file).read_text(encoding="utf-8"))
        click.echo(json.dumps({"experience_id": store.add_experience(payload), "status": "RECORDED"}, indent=2))
    except (LearningError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    finally:
        store.close()


@learn.command("candidate-lessons")
@click.option("--db", default="data/learning.db", show_default=True)
@click.option("--min-repetitions", default=2, type=click.IntRange(min=2), show_default=True)
def candidate_lessons(db: str, min_repetitions: int) -> None:
    """Generate deterministic candidate lessons from repeated failures."""
    store = _store(db)
    try:
        click.echo(json.dumps(store.failure_lesson_candidates(min_repetitions=min_repetitions), indent=2))
    finally:
        store.close()


@learn.command("recommend")
@click.option("--task-kind", required=True)
@click.option("--task-target", default=None)
@click.option("--db", default="data/learning.db", show_default=True)
def recommend(task_kind: str, task_target: str | None, db: str) -> None:
    """Return conservative strategy rankings from accumulated experience."""
    store = _store(db)
    try:
        click.echo(json.dumps(
            [item.to_dict() for item in store.strategy_recommendations(
                task_kind=task_kind,
                task_target=task_target,
            )],
            indent=2,
        ))
    finally:
        store.close()


@learn.command("snapshot")
@click.option("--db", default="data/learning.db", show_default=True)
def snapshot(db: str) -> None:
    """Show deterministic learning-ledger state."""
    store = _store(db)
    try:
        click.echo(json.dumps(store.snapshot(), indent=2))
    finally:
        store.close()


@learn.command("add-lesson")
@click.argument("json_file", type=click.Path(exists=True))
@click.option("--db", default="data/learning.db", show_default=True)
def add_lesson(json_file: str, db: str) -> None:
    """Persist a candidate or already-reviewed lesson after schema validation."""
    store = _store(db)
    try:
        payload = json.loads(Path(json_file).read_text(encoding="utf-8"))
        click.echo(json.dumps({"lesson_id": store.add_lesson(payload), "status": "RECORDED"}, indent=2))
    except (LearningError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    finally:
        store.close()


@learn.command("evolution-admission")
@click.argument("proposal_file", type=click.Path(exists=True))
@click.argument("regression_file", type=click.Path(exists=True))
@click.option("--verified-evidence-count", type=click.IntRange(min=0), required=True)
def evolution_admission(proposal_file: str, regression_file: str, verified_evidence_count: int) -> None:
    """Evaluate, without applying, a system-evolution proposal."""
    try:
        proposal = json.loads(Path(proposal_file).read_text(encoding="utf-8"))
        regression_results = json.loads(Path(regression_file).read_text(encoding="utf-8"))
        if not isinstance(regression_results, list):
            raise LearningError("regression file must contain a JSON array")
        click.echo(json.dumps(
            admission_decision(
                proposal,
                verified_evidence_count=verified_evidence_count,
                regression_results=regression_results,
            ),
            indent=2,
        ))
    except (LearningError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc


@learn.command("make-experience")
@click.option("--cycle", required=True)
@click.option("--outcome", type=click.Choice(["success", "failure", "unknown", "contradiction"]), required=True)
@click.option("--task-kind", required=True)
@click.option("--target", required=True)
@click.option("--strategy-id", required=True)
@click.option("--strategy-name", required=True)
@click.option("--observation", required=True)
@click.option("--evidence-id", multiple=True)
@click.option("--failure-class", default=None)
@click.option("--repository", default="rynahmed101-sys/automate", show_default=True)
@click.option("--revision", default=None)
@click.option("--output", type=click.Path(), required=True)
def make_experience(
    cycle: str,
    outcome: str,
    task_kind: str,
    target: str,
    strategy_id: str,
    strategy_name: str,
    observation: str,
    evidence_id: tuple[str, ...],
    failure_class: str | None,
    repository: str,
    revision: str | None,
    output: str,
) -> None:
    """Create a schema-valid experience artifact without recording it."""
    try:
        payload = build_experience(
            action_cycle_id=cycle,
            outcome=outcome,
            task_kind=task_kind,
            task_target=target,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            observation=observation,
            evidence_refs=[{"id": x} for x in evidence_id],
            failure_class=failure_class,
            repository=repository,
            revision=revision,
            correlation_id=cycle,
        )
        Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        click.echo(json.dumps({"status": "CREATED", "experience_id": payload["experience_id"], "output": output}, indent=2))
    except LearningError as exc:
        raise click.ClickException(str(exc)) from exc


@learn.command("make-evolution-proposal")
@click.option("--kind", type=click.Choice(["knowledge", "strategy", "verifier", "capability", "governance"]), required=True)
@click.option("--subject", required=True)
@click.option("--rationale", required=True)
@click.option("--benefit", required=True)
@click.option("--evidence-id", multiple=True)
@click.option("--regression", multiple=True, required=True)
@click.option("--rollback", required=True)
@click.option("--constitutional", is_flag=True)
@click.option("--output", type=click.Path(), required=True)
def make_evolution_proposal(
    kind: str,
    subject: str,
    rationale: str,
    benefit: str,
    evidence_id: tuple[str, ...],
    regression: tuple[str, ...],
    rollback: str,
    constitutional: bool,
    output: str,
) -> None:
    """Create a reviewable system-evolution proposal; never applies it."""
    try:
        payload = build_evolution_proposal(
            kind=kind,
            subject=subject,
            rationale=rationale,
            expected_benefit=benefit,
            evidence_refs=[{"id": x} for x in evidence_id],
            regression_requirements=list(regression),
            rollback=rollback,
            constitutional=constitutional,
        )
        Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        click.echo(json.dumps({"status": "CREATED", "proposal_id": payload["proposal_id"], "output": output}, indent=2))
    except LearningError as exc:
        raise click.ClickException(str(exc)) from exc
