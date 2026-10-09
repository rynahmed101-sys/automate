# Development Guide for Automate

# Development Guide

## Running tests

Install the development extra and run the test suite:

```sh
python -m pip install -e ".[dev]"
pytest -q
```

For a focused change, pass its test file(s) to pytest before running the
broader suite. The current CI definitions are in `.github/workflows/ci.yml`,
`.github/workflows/engine-ci.yml`, and `.github/workflows/security.yml`.

## Adding a calculator operation

1. Check whether an existing backend already performs the requested work.
2. Add the operation to `automate/calculator.py` and update its manifest
   description, required arguments, and dispatch.
3. Wire the same arguments through `automate calculate` in `automate/cli.py`;
   structured requests use `automate request`.
4. Add direct API, structured-request, CLI, serialization, and failure tests
   appropriate to the operation.
5. Update the README and authoritative scientific-engine ledger where needed.

The repository also retains graph/IR verification workflows. For work on those
contracts, add rule metadata to `automate/theory/rules.py`, implement the
appropriate checker behavior, and test its graph semantics. These are separate
from ordinary calculator operations.

No repository-wide formatter or linter is configured in `pyproject.toml`.
