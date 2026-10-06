# Model-Assisted Learning

Automate can optionally call a local or otherwise free/open OpenAI-compatible
reasoning service using:

- `AUTOMATE_REASONING_ENDPOINT`
- `AUTOMATE_REASONING_TOKEN` (optional for local services)
- `AUTOMATE_REASONING_MODEL`

The model is a proposal generator, not an authority. Its output is parsed,
schema-validated, and forced into CANDIDATE lesson/proposal states. It cannot
directly certify, promote, alter the ledger, change authority, or submit source
code.

This keeps the scientific system model-agnostic. A local model can be swapped
without changing the learning contracts.
