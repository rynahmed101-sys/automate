# Automate Schemas

Automate's primary calculator request and result contract is implemented in
`automate.calculator` and discovered through `calculator_manifest()`. The CLI's
`schema` command currently serves only the IR and tensor schemas.

## Current schema files

- `schemas/automate-ir-v0.1.json`: graph/IR representation used by the existing
  parse, context, validation, and verification workflows.
- `schemas/automate-tensor-v1.json`: canonical tensor-equation interchange.
- `schemas/automate-capability-inventory-v1.json`: schema for the internal
  capability evidence index at `docs/CAPABILITY_INVENTORY.json`.
- `schemas/automate-data-query-v1.json` and
  `schemas/automate-data-evidence-v1.json`: structured data-query/evidence
  contracts. They currently have no CLI schema-discovery command or calculator
  operation consumer.
- `schemas/automate-operating-mode-v1.json`: retained operating-mode contract;
  it is not part of the public calculator request protocol.

Discover the schemas exposed by the CLI with:

```sh
automate schema --name ir
automate schema --name tensor
```

The older AI proposal/context/agent-control and certificate-package schema
contracts have been retired. They are not required to call the calculator.

## Calculator principle

An AI should not need to manufacture a proposal object, obtain an approval
status, or construct a certificate package just to ask Automate to calculate
something. The preferred interaction is request, calculation, result, with
optional diagnostics where useful.
