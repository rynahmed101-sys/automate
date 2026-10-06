# Autonomous Development Game Plan

## Purpose

Automate should advance continuously without confusing speed with authority.

OBSERVE -> PLAN -> PREPARE -> WORK -> INSPECT -> TEST -> RECONCILE -> VERIFY -> CERTIFY -> ADVANCE

A slow worker, queued CI, or unavailable external worker is not itself a reason for Automate to stop. When one lane waits, Automate should perform other safe work that does not cross an evidence boundary.

## Boss boundary

Automate owns roadmap order, capability ownership, file boundaries, proposal validation, independent tests, Git lifecycle, merge/certification decisions, recovery, and the durable distinction between evidence and claims.

Workers may propose implementation. They may not promote their own trust level.

## Work lanes

1. Capability: implement the earliest legitimate mathematical/physics capability.
2. Verification: adversarial cases, cross-checks, and evidence quality.
3. Reconciliation: stale branches, inventory drift, duplicate ownership, control-plane defects.
4. Research: inspect mature mathematics/physics implementations and extract patterns, not authority.
5. Infrastructure: worker contracts, evidence receipts, scheduling, recovery, machine-agent interfaces.
6. CI: improve feedback speed without weakening authoritative verification.

A lane may proceed only when independent of blocked or unverified work.

## Evidence

Meaningful autonomous actions should record the exact repository/base SHA, target, packet/result identifiers, changed-file hashes, focused tests, independent verification, CI/security identifiers, branch/PR/merge SHA, trust state, unresolved issues, and timestamp.

Trust states are distinct:
PLANNED -> IMPLEMENTED -> LOCALLY_TESTED -> DEV_CI_VERIFIED -> MERGED_MAIN -> EXACT_HEAD_VERIFIED -> SECURITY_VERIFIED -> INDEPENDENTLY_CROSS_CHECKED -> CERTIFIED

No lower-trust evidence may masquerade as a higher-trust state.

## Research policy

External repositories, papers, datasets, examples, and AI-generated research are evidence sources, not authorities. Convert useful research into reusable capability requirements, backend/adapters, tests or counterexamples, provenance, or design patterns.

## Recovery

Classify failures, preserve evidence, minimize the failing surface, retry only permitted failure classes, repair the smallest responsible layer, rerun focused evidence, then return to authoritative verification.

## Advancement

After each action, recompute the next safe action from the phase ledger, live Git state, capability inventory, active branches/PRs, evidence receipts, and current verification state.

## Immediate sequence

W0: finish the autonomous contract foundation without enabling live workers.
W1-W2: harden the machine worker API and provider-neutral model boundary.
W3: make repository context packet-authorized and provenance-preserving.
W4-W5: make proposal application and PR lifecycle independently testable.
W6: make reconciliation/recovery a first-class supervisor function.
W7: support bounded one-capability-at-a-time autonomous cycles.
W8: add controlled self-healing.

In parallel, continue mathematical development only at the earliest legitimate ledger frontier: Stage 1B improper integrals and convergence-aware handling.

## Activation rule

A real external capability worker remains OFF until every readiness gate has independent evidence. A dry run is not a merge. A worker result is not proof. A green PR run is not exact-head certification.

## Continuous means non-idle

Continuous does not mean uncontrolled. When one lane is blocked, another safe lane is selected automatically. Stop only when no safe action remains, an authority boundary requires human judgment, or a failure requires escalation.
