# Contributing to Automate

Contributions should extend the local-first scientific calculator without
duplicating mature symbolic or numerical backends.

## Principles

- Keep AI interpretation outside Automate; expose reusable calculation
  operations with clear inputs and results.
- Preserve assumptions and domain restrictions where the operation represents
  them.
- Keep graph/IR verification behavior distinct from direct calculator results.
- Keep the core usable without cloud AI providers.

## Pull request checklist

1. Add focused positive and negative tests for changed behavior.
2. Keep the Python API, manifest, CLI, and README consistent for new calculator
   operations.
3. Run the affected tests and, where practical, `pytest -q`.
4. Run `automate demo` when changing the end-to-end graph workflow.
5. Document the actual verification scope; do not describe CI success as
   formal proof.
