# Autonomous Scientific Development Ecosystem

> **System authority:** The complete architecture is maintained in `docs/AUTONOMOUS_SYSTEM_MASTER_PLAN.md`. This document is the operational ecosystem view.

## The reconciled model

The Verification & Reconciliation Engine is a **logical subsystem spanning all three repositories**, not a fourth monolithic application.

```
                         AUTOMATE
          canonical maths/physics + authority
                         │
                         ▼
             Verification & Reconciliation
                    logical engine
                  /                   \
                 ▼                     ▼
            CHANFANA               THE MIRROR
       durable execution        scientific laboratory
       queues / leases          simulation / perturbation
       recovery / auth          numerical diagnostics
       transport / provenance  counterexamples / discovery
                 \                     /
                  ▼                   ▼
                    verifiable packet
                         │
                         ▼
                      AUTOMATE
                 final decision
```

Chanfana is an internal execution/control substrate of the verifier. Mirror is a scientific execution compartment of the verifier when laboratory work is required. Automate remains the authority.

## Ownership

### Automate

Automate owns canonical mathematical and physical semantics, capability ordering, inventory, rule registries, authoritative contracts, acceptance policy, Git promotion, exact-head verification, security evidence, and certification.

Automate does not need to contain every verification operation. It provides the canonical scientific machinery and the final authority boundary that the verifier must respect.

### Chanfana

Chanfana owns durable machine execution:

- authenticated worker boundaries;
- durable jobs and queues;
- leases and heartbeats;
- stale-job recovery;
- retries and dead-letter handling;
- resource and time bounds;
- structured packet/result transport;
- execution/evidence persistence.

Chanfana also owns the reusable control-plane compartments used by the verifier. It does not own scientific truth or certification.

### THE MIRROR

Mirror owns the laboratory:

- hypothesis/model execution;
- simulation;
- perturbation and parameter sweeps;
- numerical diagnostics;
- stability/convergence investigation;
- counterexample searches;
- discovery analysis;
- reproducible experimental provenance;
- experimental evidence.

Mirror is richer than a passive checker by design. That richness can be used to clear verification backlog items, but Mirror remains a laboratory and does not become an authority.

## What the Verification Engine actually does

The verifier connects these capabilities and supplies the missing reasoning layer.

It should:

1. inventory the exact repository/PR/capability state;
2. identify inconsistencies and likely causes;
3. distinguish implementation errors from bad tests, bad contracts, missing assumptions, numerical artifacts, data/provenance problems, and unresolved scientific behavior;
4. choose the appropriate deterministic, mathematical, computational, data, CI, or laboratory evidence path;
5. request Chanfana jobs when work must be durable;
6. use Mirror machinery when scientific experimentation is actually required;
7. propose and apply the smallest safe repair under explicit policy;
8. rerun focused evidence;
9. preserve complete lineage;
10. emit a verifiable packet.

It cannot certify or promote a capability.

## Shared compartments

Shared compartments are allowed where they prevent needless duplication:

- versioned packets and job contracts;
- correlation IDs and provenance;
- evidence normalization;
- failure classifications;
- repair request/result envelopes;
- CI/security receipt interfaces;
- experiment request/result envelopes;
- verifiable-packet assembly.

Shared does not mean two competing implementations. Each shared capability needs a clear implementation owner and one contract.

## Backlog policy

The Stage 1A–3A verification backlog is the verifier's first real workload and acceptance test.

Mirror/external-world research remains ON HOLD as an autonomous discovery source. Mirror's existing local laboratory may nevertheless be used for bounded verification work when a backlog item genuinely needs simulation, perturbation, numerical diagnosis, or counterexample search.

That gives us the useful part of Mirror now without opening the floodgates to uncontrolled scientific exploration.

## Repair policy

```
failure
 → classify
 → diagnose
 → identify responsible layer
 → smallest safe repair
 → focused rerun
 → independent evidence
 → packet
```

Never:

```
failure → weaken evidence → pass → certify
```

The verifier must prefer an unresolved anomaly over a false positive.

## Permanent loop

```
frontier
 → verifier intake
 → Chanfana durable execution
 → deterministic / mathematical / Mirror evidence
 → diagnosis
 → bounded repair
 → evidence packet
 → Automate decision
 → next frontier
 → repeat
```

After the backlog is cleared and readiness gates are satisfied, the same architecture can support continuous capability discovery. `main` remains the authority surface; `engine` remains the development trunk.
