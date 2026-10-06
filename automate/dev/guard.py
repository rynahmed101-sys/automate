"""Git/branch guardrails for capability packets."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from automate.dev.inventory import load_inventory


def changed_files(base: str | None = None, head: str = "HEAD") -> list[str]:
    if base:
        cmd = ["git", "diff", "--name-only", f"{base}...{head}"]
    else:
        cmd = ["git", "diff", "--name-only", "HEAD^", head]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def validate_branch_scope(branch: str, files: list[str]) -> list[str]:
    data = load_inventory()
    shared = set(data["branch_policy"]["shared_integration_files"])
    errors: list[str] = []

    if branch.startswith("feat/"):
        touched = sorted(shared.intersection(files))
        if touched:
            errors.append(
                "Capability branches must not modify shared integration files: "
                + ", ".join(touched)
            )
    elif branch.startswith("integrate/"):
        return errors
    elif branch.startswith("hotfix/"):
        return errors
    else:
        errors.append(
            f"Unsupported development branch '{branch}'. Use feat/<capability> "
            "for isolated capability work or integrate/<batch> for reconciliation."
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--changed-file", action="append", dest="changed_files")
    args = parser.parse_args()
    files = args.changed_files if args.changed_files is not None else changed_files(args.base, args.head)
    errors = validate_branch_scope(args.branch, files)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"BRANCH_SCOPE_OK: {args.branch} ({len(files)} changed files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
