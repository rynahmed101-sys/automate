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
