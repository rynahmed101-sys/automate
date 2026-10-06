"""CLI commands for the development control plane."""
from __future__ import annotations

import json
import click

from automate.dev.inventory import (
    InventoryError,
    active_references,
    get_capability,
    load_inventory,
    next_action,
    next_unclaimed,
    packet as capability_packet,
    queue_snapshot,
    validate_inventory,
)


@click.group(name="capability")
def capability() -> None:
    """Inspect capability ownership, reconciliation and verification state."""


@capability.command("list")
@click.option("--stage", default=None)
@click.option("--state", default=None)
@click.option("--json", "as_json", is_flag=True)
def list_capabilities(stage: str | None, state: str | None, as_json: bool) -> None:
    data = load_inventory()
    records = [
        item for item in data["capabilities"]
        if (stage is None or item["stage"] == stage)
        and (state is None or item["implementation_state"] == state)
    ]
    if as_json:
        click.echo(json.dumps(records, indent=2))
    else:
        for item in records:
            click.echo(f'{item["stage"]:>3}  {item["implementation_state"]:<24}  {item["id"]}')


@capability.command("status")
@click.argument("capability_id")
@click.option("--json", "as_json", is_flag=True)
def status(capability_id: str, as_json: bool) -> None:
    try:
        item = get_capability(capability_id)
    except InventoryError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        click.echo(json.dumps(item, indent=2))
        return
    click.echo(f'{item["id"]}: {item["implementation_state"]}')
    click.echo(f'{item["name"]}')
    click.echo(f'authority: {item["authority"]["kind"]} / {item["authority"]["ref"]}')
    for ref in item["references"]:
        if ref.get("type") == "pr":
            click.echo(f'PR #{ref.get("number")}: {ref.get("state")} {ref.get("branch", "")}'.rstrip())


@capability.command("next")
@click.option("--json", "as_json", is_flag=True)
def next_command(as_json: bool) -> None:
    data = load_inventory()
    candidate = next_unclaimed(data)
    payload = {
        "next_action": next_action(data),
        "next_unclaimed": candidate["id"] if candidate else None,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(json.dumps(payload["next_action"], indent=2))


@capability.command("refs")
@click.option("--json", "as_json", is_flag=True)
def refs(as_json: bool) -> None:
    records = active_references(load_inventory())
    if as_json:
        click.echo(json.dumps(records, indent=2))
    else:
        for ref in records:
            click.echo(f'PR #{ref.get("number")}: {ref["capability_id"]} / {ref.get("branch", "")}')


@capability.command("validate")
@click.option("--json", "as_json", is_flag=True)
def validate(as_json: bool) -> None:
    data = json.loads(__import__("pathlib").Path(
        __import__("automate.dev.inventory", fromlist=["INVENTORY_PATH"]).INVENTORY_PATH
    ).read_text(encoding="utf-8"))
    errors = validate_inventory(data)
    payload = {"valid": not errors, "errors": errors}
    click.echo(json.dumps(payload, indent=2) if as_json else ("VALID" if not errors else "\n".join(errors)))
    if errors:
        raise click.exceptions.Exit(1)


@capability.command("packet")
@click.argument("capability_id")
@click.option("--json", "as_json", is_flag=True)
def packet_command(capability_id: str, as_json: bool) -> None:
    """Print the machine-readable implementation contract for one capability."""
    try:
        payload = capability_packet(capability_id)
    except InventoryError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(payload, indent=2) if as_json else json.dumps(payload, indent=2))


@capability.command("guard")
@click.option("--branch", required=True, help="Development branch being checked.")
@click.option("--base", default=None, help="Base ref/commit used for changed-file discovery.")
@click.option("--head", default="HEAD", help="Head ref/commit.")
@click.option("--changed-file", multiple=True, help="Explicit changed-file path; repeatable.")
def guard_command(branch: str, base: str | None, head: str, changed_file: tuple[str, ...]) -> None:
    """Fail closed when a capability branch crosses shared integration boundaries."""
    from automate.dev.guard import changed_files, validate_branch_scope
    files = list(changed_file) if changed_file else changed_files(base, head)
    errors = validate_branch_scope(branch, files)
    if errors:
        for error in errors:
            click.echo(f"ERROR: {error}", err=True)
        raise click.exceptions.Exit(1)
    click.echo(f"BRANCH_SCOPE_OK: {branch} ({len(files)} changed files)")


@capability.command("queue")
@click.option("--json", "as_json", is_flag=True)
def queue_command(as_json: bool) -> None:
    """Print the complete deterministic capability queue state."""
    payload = queue_snapshot(load_inventory())
    click.echo(json.dumps(payload, indent=2) if as_json else json.dumps(payload, indent=2))


@capability.command("audit-live")
@click.option("--repo", "repository", required=True, help="GitHub repository in owner/name form.")
@click.option("--json", "as_json", is_flag=True)
def audit_live_command(repository: str, as_json: bool) -> None:
    """Cross-check inventory references against live open GitHub PRs."""
    from automate.dev.live import LiveAuditError, summarize_live
    try:
        payload = summarize_live(repository)
    except LiveAuditError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(payload, indent=2) if as_json else ("VALID" if payload["valid"] else "\n".join(payload["errors"])))
    if not payload["valid"]:
        raise click.exceptions.Exit(1)
