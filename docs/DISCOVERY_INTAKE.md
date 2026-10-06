# Discovery Intake

Mirror can produce a candidate capability, but Automate must first triage it.

The intake layer compares the candidate against the canonical capability
inventory and returns one of:

- `READY_FOR_INVESTIGATION`
- `BLOCKED_UNKNOWN_PREREQUISITES`
- `BLOCKED_INCOMPLETE_PREREQUISITES`
- `COLLIDES_WITH_CANONICAL_CAPABILITY`

The intake layer never edits `docs/CAPABILITY_INVENTORY.json`.

A ready candidate still requires bounded scientific investigation, independent
verification, regression construction, implementation, PR review, exact-head
verification, security verification, and normal capability-authority promotion
before it can become canonical.

This is the missing bridge between Mirror discovery and the existing strict
capability ladder.
