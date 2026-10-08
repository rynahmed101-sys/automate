# Autonomous Development Game Plan

## Purpose

Automate should advance continuously without confusing speed with authority.

OBSERVE → PLAN → PREPARE → WORK → INSPECT → TEST → RECONCILE → VERIFY → PACKET → AUTHORIZE → ADVANCE

The Verification & Reconciliation Engine is the reasoning layer that performs the middle of this loop. It is distributed across the three repositories rather than trapped inside one.

## Ownership model

- **Automate:** canonical maths/physics, capability ledger, inventory, acceptance policy, Git promotion, certification.
- **Chanfana:** durable execution, queues, leases, recovery, authentication, resource limits, transport, evidence persistence, verifier control-plane primitives.
- **Mirror:** scientific laboratory execution, simulation, perturbation, numerical diagnostics, counterexamples, discovery analysis, experimental provenance.
- **Verification Engine:** diagnoses failures, selects evidence, coordinates repairs and checks, reconciles repository state, and builds verifiable packets. It has no certification authority.

## The verifier's hard job

The verifier must know what to correct and why.

A failure is not automatically an implementation bug:

```
failure
 ├─ implementation defect?
 ├─ test defect?
 ├─ contract defect?
 ├─ missing assumption?
 ├─ numerical precision/discretization issue?
 ├─ backend mismatch?
 ├─ data/provenance corruption?
 ├─ CI/environment issue?
 ├─ genuine contradiction?
 └─ unresolved scientific behavior?
```

Only after diagnosis may a bounded repair be proposed.

The repair loop is:

```
diagnose
 → smallest safe repair
 → preserve/strengthen tests
 → rerun
 → compare independent evidence
 → record lineage
```

Deleting or weakening the evidence that exposed the problem is forbidden.

## Work lanes

1. Capability implementation at the earliest legitimate ledger frontier.
2. Verification and mathematical cross-checks.
3. Repository reconciliation and stale-branch cleanup.
4. Controlled repair and regression protection.
5. Research of mature implementations and literature.
6. Chanfana execution/control infrastructure.
7. Mirror scientific experiments required by verification.
8. CI/security evidence.

A blocked lane must not silently grant permission to leapfrog the ledger.

## Shared machinery rule

Use one contract and one clear owner for shared compartments. Do not build duplicate queue, provenance, evidence, experiment-envelope, or repair-envelope systems merely because the logic crosses repository boundaries.

Chanfana should carry durable verifier jobs. Mirror should execute scientific work that actually requires laboratory machinery. Automate should execute or expose canonical mathematical checks and preserve authority.

## Backlog-first operation

The current Stage 1A–3A backlog is the verifier's first production workload and acceptance test.

For each item:

```
inventory
 → dependency graph
 → diagnose
 → bounded repair if justified
 → deterministic tests
 → mathematical/computational checks
 → optional Mirror experiment
 → CI/security
 → exact-head evidence
 → verifiable packet
 → Automate decision
```

Mirror/external-world discovery remains ON HOLD during this backlog phase. Existing local Mirror capabilities may be used when they are part of a bounded verification task.

## Activation order

Do not enable a generic external worker merely because the contracts exist.

First prove:

1. durable Chanfana job execution;
2. fail-closed packet/result validation;
3. repository reconciliation;
4. bounded repair with rollback/lineage;
5. canonical mathematical checks;
6. Mirror experiment request/result boundary;
7. evidence normalization;
8. verifiable-packet generation;
9. exact-head and Security Audit evidence;
10. end-to-end dry run.

Only then activate broader autonomous workers.

## Continuous operation

When one lane waits, the system selects another safe lane. It stops only when no safe action remains, authority is required, or evidence is insufficient.

After the current backlog is cleared:

```
verify/reconcile
 → packet
 → Automate authority decision
 → capability frontier
 → research/design
 → bounded implementation
 → repeat
```

The cycle is intentionally endless. The machinery is allowed to keep working so humans can return to their ancient tradition of sleeping occasionally.
