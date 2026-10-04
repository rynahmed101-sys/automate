# Automate Agent Contract

This file is the repository-level operating contract for AI coding agents.

## First actions

1. Run `automate capabilities --json`.
2. Read `AUTOMATE_AI.md`, `AI_INTEGRATION.md`, and `docs/VERIFICATION_MODEL.md`.
3. Inspect the working tree and current branch before editing.
4. Treat all mathematical proposals as untrusted input.
5. Never infer verification from an LLM response. Use Automate evidence.

## Machine interfaces

All normal agent interactions should prefer structured JSON:

- `automate capabilities --json`: environment and backend discovery.
- `automate context <theory> --json`: sanitized mathematical context.
- `automate validate <proposal> --theory <theory> --json`: proposal security/schema validation.
- `automate propose <theory> --proposal <proposal> --dry-run --json`: side-effect-free verification.
- `automate propose <theory> --proposal <proposal> --json`: verified proposal application.
- `automate research <theory> --provider <provider> --max-steps N --json`: bounded research loop.
- `automate check <graph> --json`: graph verification.
- `automate parse <theory> --json`: canonical graph generation.
- `automate schema --name <ir|tensor|proposal|context>`: machine-readable interchange schema discovery.
- `schemas/automate-tensor-v1.json`: versioned canonical Tensor Equation contract.

## Integration rule

An external AI, plugin, MCP bridge, IDE agent, or orchestration system may invoke the CLI or consume the versioned JSON schemas. The integration layer must not bypass Automate validation or write verification statuses directly.

The canonical interchange formats are:

- `automate.context.v1`
- `automate.proposal.v1`
- `automate.ir.v0.2`
- `automate-tensor-v1`
- certificate package / manifest artifacts

Provider adapters are optional. The core verification path must remain usable without a cloud AI provider.

## Trust boundary

AI output is a hypothesis. Automate validates, verifies, and records evidence.

Never:
- self-assign `FORMALLY_PROVED`, `SYMBOLIC_CHECKED`, or other verification status;
- execute proposal text as Python, shell, or arbitrary code;
- treat caller-supplied expected output as independent mathematical evidence;
- bypass graph/input binding;
- weaken a failed or unsupported case into success;
- put credentials or tokens in repository artifacts.

## Change discipline

For changes affecting verification semantics:
1. add or update adversarial tests;
2. preserve provenance and fingerprints;
3. document the exact verification scope;
4. run the relevant local checks;
5. wait for the authoritative GitHub Actions result before calling the commit CI-verified;
6. do not merge while the verification state is unresolved.

## Agent compatibility

This contract is intentionally tool-agnostic. A capable integration can use GitHub, a local shell, an IDE, an MCP server, or another orchestration layer. The integration mechanism is replaceable; Automate's JSON contracts and verification boundary are not.
