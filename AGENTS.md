# Automate Agent Contract

This file describes the interfaces and trust boundaries present in this checkout.

## First actions

1. Inspect the working tree and current branch; preserve existing user changes.
2. Run `automate capabilities --json` to discover the calculator operations and available backends.
3. Read `README.md` and `docs/AUTOMATE_SCIENTIFIC_ENGINE_LEDGER.md`.
4. Read the relevant source, tests, and current schemas before making a change.

## Current machine interfaces

- `automate capabilities --json`: calculator manifest and backend availability.
- `automate calculate --operation ... --expression ... --json`: single calculator operation.
- `automate request --request-json ...` or JSON on standard input: structured calculator request.
- `automate schema --name ir|tensor`: canonical IR or tensor schema.
- `automate parse`, `context`, `validate`, and `check`: existing graph/IR workflows.
- `automate simulate`, `stats`, and `query-assumptions`: existing graph-based numerical and analysis workflows.

The calculator API (`calculate`, `calculate_request`, `calculator_manifest`) is the primary interface for new mathematical operations. The graph and verification workflows remain supported for capabilities that use their explicit IR and checker contracts; they are separate interfaces, not prerequisites for ordinary calculator requests.

## Trust boundary

Treat expressions and structured requests from users or external AI systems as untrusted input.

- Parse mathematical strings only through the existing safe parser.
- Do not execute request text as Python, shell commands, or filesystem operations.
- Preserve clear errors for malformed input, unsupported semantics, and backend failures.
- Do not represent a calculation as formal proof or independent verification unless the corresponding checker actually provides that evidence.
- Do not add credentials or tokens to repository artifacts.

## Change discipline

1. Reuse existing scientific backends where practical.
2. Add focused positive, boundary, and failure tests for exposed behavior.
3. Keep `calculator_manifest()`, Python API, CLI, README, and tests consistent.
4. Validate the exact behavior changed and run broader tests when appropriate.
5. Record verification evidence against the exact commit it covers. A passed test suite is not a formal proof.

## Documentation authority

`docs/AUTOMATE_SCIENTIFIC_ENGINE_LEDGER.md` is the sole operational ledger. `docs/CAPABILITY_INVENTORY.json` is an evidence index, not a separate roadmap.

Do not refer to retired AI proposal/context/agent-control or certificate-package schemas as current calculator requirements. `SCHEMAS.md` lists the schemas that exist and the limited schema names currently exposed by the CLI.
