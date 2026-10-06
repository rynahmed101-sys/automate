# Autonomous Scientific Development Ecosystem

## Purpose

Automate, the Chanfana worker substrate, and THE MIRROR form one bounded development system with one authority boundary.

The system is:

```text
AUTOMATE
  authoritative roadmap + capability semantics + verification
        |
        | bounded worker packet
        v
CHANFANA WORKER
  durable jobs + leases + bounded model execution
        |
        | experiment/research request
        v
THE MIRROR
  executable hypotheses + simulation + perturbation + discovery
        |
        | reproducible evidence packet
        v
CHANFANA WORKER
        |
        | worker result + evidence receipts
        v
AUTOMATE
  independent inspection -> tests -> reconciliation -> CI/security
  -> merge -> certification -> next capability
```

No repository may silently become another repository's authority.

## Ownership

### Automate

Automate is the authority for:

- development-stage order;
- capability ownership and dependency state;
- canonical mathematical and physical semantics;
- allowed worker boundaries;
- proposal validation and application;
- Git branch and PR lifecycle;
- independent verification;
- exact-head and security evidence;
- certification;
- recovery and reconciliation;
- the distinction between evidence and claims.

The phase ledger remains the sole roadmap authority. The capability inventory remains implementation-state authority.

### Chanfana worker substrate

The worker repository provides bounded execution infrastructure:

- authenticated machine-facing API;
- durable job state;
- queue dispatch;
- execution leases and heartbeats;
- stale-job recovery;
- bounded retries and dead-letter handling;
- wall-clock observability;
- replaceable model-provider boundary.

The worker is an execution mechanism, not a Git authority and not a scientific authority.

### THE MIRROR

Mirror is the experimental laboratory:

- formalize hypotheses;
- construct executable models;
- run simulations;
- perturb parameters and initial conditions;
- repeat and stress-test;
- analyze observations;
- compare models or references when useful;
- preserve reproducibility and provenance;
- produce evidence packages.

Mirror may discover disagreement with established theory. That disagreement is preserved as evidence and does not become an Automate fact without independent verification.

Mirror must not modify Automate's ledger, inventory, registry, certification state, or repository history.

## Evidence flow

Every cross-repository action should retain stable correlation identifiers:

- `action_cycle_id`
- `capability_id`
- `packet_id`
- `job_id`
- `result_id`
- experiment/run identifiers when Mirror is involved
- source revision or commit SHA
- changed-file hashes
- focused test results
- independent checks
- CI and Security Audit identifiers where applicable
- final exact-head SHA when available.

The minimum trust progression is:

```text
proposal
  -> worker result
  -> experimental evidence
  -> independent Automate inspection
  -> focused tests
  -> reconciliation
  -> merged main
  -> exact-head verification
  -> security verification
  -> independent cross-check
  -> certification
```

A lower stage must never be represented as a higher stage.

## Mirror evidence is not Automate proof

Mirror's raw observations are authoritative only within the laboratory's own evidence model.

For Automate they are external evidence.

A Mirror result may therefore be:

- relevant;
- reproducible;
- numerically strong;
- surprising;
- useful for designing tests;
- useful for discovering counterexamples;

without being certified mathematical truth.

Promotion requires an Automate-side verification route appropriate to the claim.

## Research and data

External repositories, papers, datasets, structured-data providers, and model outputs are research inputs.

They must enter through bounded, provenance-preserving contracts.

The preferred path is:

```text
research/data request
  -> bounded provider or laboratory execution
  -> provenance + content hash + limits
  -> evidence packet
  -> worker reasoning
  -> independent verification
```

A provider never becomes authoritative merely because it returned a record.

Provider adapters should remain replaceable. Local/open scientific tools are preferred when they provide a reliable independent route.

## Activation gates

The real capability worker remains OFF until the combined system can demonstrate:

1. Automate worker packet/result contracts are implemented and tested.
2. The worker API is authenticated and durably bounded.
3. Worker output is independently validated.
4. Worker branch/PR lifecycle is safely exercised.
5. Live control-plane audit passes.
6. Mirror's experimental interface can produce reproducible evidence without granting repository authority.
7. Cross-repository identifiers and provenance survive the complete round trip.
8. An end-to-end dry run succeeds without a real merge.
9. Exact-head and Security Audit remain authoritative for Automate.
10. No unresolved control-plane collision or stale ownership remains.

Queue provisioning or deployment evidence is a runtime-readiness concern. It must not be confused with the scientific architecture itself.

## Capability advancement

When infrastructure is waiting, the system should continue safe work in independent lanes.

The strict mathematical frontier remains the earliest incomplete capability in the phase ledger. Infrastructure work may support that capability but may not use infrastructure readiness as permission to leapfrog the ledger.

The first autonomous capability target remains:

**Stage 1B: improper integrals and convergence-aware handling.**

A worker may research, implement, test, and propose this capability. Automate remains responsible for reconciliation, merge, exact-head verification, security verification, and certification.

## Permanent boundary

The system is not:

```text
AI -> arbitrary code -> merge -> truth
```

It is:

```text
AI proposal -> bounded execution -> recorded evidence
             -> independent judgment -> authoritative verification
             -> certified capability
```

That boundary is the mechanism by which autonomy earns trust.
