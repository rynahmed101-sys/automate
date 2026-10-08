# Triad integration boundary

This directory is the controlled consolidation of the former Chanfana Worker Substrate and THE MIRROR into the Automate canonical repository.

## Authority

Automate remains the sole authority for:
- capability ordering and the phase ledger;
- mathematical and physical semantics;
- verification and certification;
- promotion and Git authority;
- autonomous-cycle decisions.

Imported subsystems are implementation/evidence machinery. Their outputs remain untrusted until Automate validates them.

## Integrated subsystems

- `integrations/chanfana/`: bounded execution substrate, worker packets, queue/job lifecycle, leases/recovery, result guards, research/verification/Mirror envelopes, and HTTP endpoint surface.
- `integrations/mirror/`: experimental laboratory, mission execution, persistent brain, reasoning/inference, research, simulation/tooling, frontier worker, evidence generation, and bounded GitHub proposal machinery.

## Boundary rule

The import preserves subsystem provenance and local build manifests. It does not grant either subsystem authority to certify Automate capabilities or mutate the authoritative ledger.

## Consolidation sequence

1. Import source and tests without semantic rewrites.
2. Reconcile contracts against Automate's canonical schemas and exact-head rules.
3. Add integration tests proving packet -> worker -> evidence -> Automate validation.
4. Remove duplicate cross-repository machinery only after the integrated path is certified.
5. Retire the former repositories only after their functionality is demonstrably contained here and their external deployment responsibilities have been migrated.

Source revisions:
- Chanfana: `main` at integration start.
- Mirror: `main` at integration start.

This document is a consolidation record, not a replacement for `docs/AUTONOMOUS_SYSTEM_MASTER_PLAN.md` or `docs/PROJECT_PHASE_LEDGER.md`.
