# Autonomous Scientific System Master Plan

**Status:** AUTHORITATIVE SYSTEM MAP  
**Owner:** Automate primary integrator  
**Scope:** Automate + Chanfana Worker Substrate + Verification & Reconciliation Engine + THE MIRROR + external research/data providers  
**Last reviewed:** 2026-10-08

> **This is the single system-level architecture and infrastructure authority for the autonomous scientific ecosystem.**
>
> Other planning, architecture, role, and handoff documents are subordinate references. If they conflict with this document, this document wins. Capability ordering remains detailed in `docs/PROJECT_PHASE_LEDGER.md`, but the ledger does not redefine system architecture, repository roles, worker authority, deployment state, or readiness.

## 1. What we are building

The system is not a single autonomous AI and it is not a cloud worker with some mathematics attached.

It is a controlled scientific development loop:

```
Capability frontier
      ↓
Automate proposes / specifies bounded work
      ↓
Execution substrate runs bounded work
      ↓
External research/data sources may provide evidence
      ↓
THE MIRROR performs experiments, numerical checks,
perturbations, counterexample searches, and observations
      ↓
Verification & Reconciliation Engine evaluates evidence and produces a verifiable packet; Automate makes the authoritative decision
      ↓
the Verification Engine performs applicable mathematical/evidence checks without requiring conformity to established physics
      ↓
Proposal enters reviewable Git history
      ↓
CI + Security + exact-head verification
      ↓
Certified main
      ↓
New capability frontier
```

The important boundary is:

**Evidence can influence investigation. Evidence cannot directly become authority.**

No worker, database, search result, external model, scientific package, Mirror experiment, or AI-generated proposal may self-certify a capability.

## 2. Repository roles

### Automate — authority, canonical semantics, and acceptance surface

Automate owns:

- canonical mathematical and physics semantics;
- capability representation and rule registry;
- canonical mathematical and physics semantics, verification rules, and supported verification backends used by the Verification Engine;
- capability inventory;
- phase/capability ordering;
- worker packet and result contracts;
- research/data request and evidence contracts;
- autonomous-cycle orchestration;
- readiness gates;
- evidence receipts;
- Git proposal/promotion logic;
- certification state.

Automate is the only repository allowed to decide that a capability becomes authoritative or certified. The Verification Engine may only produce evidence and verifiable packets.

Its `engine` branch is the living development trunk.

Its `main` branch is the certified release surface.

### Chanfana — durable execution, transport, and system memory

`rynahmed101-sys/chanfana-openapi-template` is the durable substrate connecting the other two environments. It owns:

- durable job persistence;
- queue dispatch;
- execution leases;
- heartbeats;
- stale-job recovery;
- retry/requeue behavior;
- worker API boundaries;
- runtime resource/time limits;
- structured job/result transport;
- durable learning and experience storage used as operational memory for Automate and the wider system;
- correlation/provenance persistence across long-running work.

The learning store is memory, not truth. It may retain experiences, lessons, research proposals/results, evolution proposals/plans, repair outcomes, and other bounded artifacts, while preserving source revision, correlation ID, hashes, and authority labels.

Chanfana does **not** decide mathematical truth or certification and does not rewrite Automate's ledger. It makes the system durable enough to learn from what happened and resume work after interruptions.

Its `engine` branch is the living infrastructure development trunk.

Its `main` branch is the release surface.

### THE MIRROR — autonomous AI engineering partner, research brain, and scientific laboratory

`rynahmed101-sys/the-mirror` is the system's general-purpose AI engineering environment. It is simultaneously:

- the scientific laboratory for unusual or established mathematics/physics;
- a research and discovery engine;
- a software-engineering workspace;
- a diagnosis and repair engine;
- a capability-generation partner for Automate;
- a source of independent verification work when the claim needs experimentation rather than repository-only checks.

Mirror owns:

- hypotheses and model formalization;
- scholarly and code research;
- executable experiment design;
- simulations, perturbations, parameter sweeps, and numerical diagnostics;
- counterexample and failure searches;
- capability design and implementation proposals;
- diagnosis of implementation, integration, numerical, test, provenance, and CI failures;
- bounded repairs and repair proposals;
- reproducible provenance and evidence;
- follow-up work and discovery candidates.

Mirror may create and modify code in its own repository and may prepare bounded capability/repair changes for Automate through reviewable Git proposals or worker handoffs. Mirror may recommend or implement a correction; it may not certify the correction, promote itself, change Automate's canonical ledger/certification records, or bypass Automate's acceptance gates.

Its observations and engineering output are not dismissed merely because they are produced by an AI. They are evaluated according to the relevant evidence class, reproducibility, independent checks, CI, and Automate's authority boundary.

Its `engine` branch is the living development trunk.

Its `main` branch is the release surface.

### Persistent self-development loop

The three repositories are treated as one continuously operating system, not three unrelated projects:

```
observe canonical state
  ↓
repair defects / reconcile stale work
  ↓
select the earliest eligible capability
  ↓
Automate specifies the bounded objective
  ↓
Mirror researches, designs, codes, experiments, or repairs
  ↓
Chanfana transports the work and persists execution + learning memory
  ↓
Automate / Verification Engine evaluates evidence and integration
  ↓
reviewable Git mutation
  ↓
CI + Security + exact-head verification
  ↓
promotion / bookkeeping
  ↓
record the actual outcome in durable memory
  ↓
recompute the frontier
  ↓
repeat indefinitely
```

Mutation is therefore allowed, but it is bounded, attributable, reversible through Git history, and evidence-gated. Self-development does not mean self-certification and does not mean unconstrained self-rewriting.

### External research/data workers — evidence acquisition, currently OFF

This is a separate worker class from the implementation worker.

A research worker may:

- search the web or scientific repositories;
- inspect papers, documentation, datasets, and code;
- query structured data services;
- use BigQuery-like systems when available;
- gather independent implementations;
- return source metadata and bounded evidence.

It may **not**:

- modify Automate source directly;
- modify the phase ledger;
- modify the capability inventory;
- certify a capability;
- decide that its own evidence is sufficient;
- bypass Mirror or Automate verification where those are required.

The current Automate contracts already anticipate this class through:

- `automate/dev/research.py`;
- `automate/dev/data.py`;
- `schemas/automate-research-request-v1.json`;
- `schemas/automate-research-evidence-v1.json`;
- `schemas/automate-data-query-v1.json`;
- `schemas/automate-data-evidence-v1.json`.

**Research/data worker activation is currently OFF.**

BigQuery is therefore an optional provider, not a foundational dependency. The architecture deliberately supports SQL services, BigQuery-like services, DuckDB/local data, scientific repositories, and other bounded providers behind the same evidence contract.

## 3. The infrastructure milestones

These are infrastructure milestones, not mathematical capability milestones.

### I0 — System governance and authority map

**Goal:** Every AI can determine who owns what before changing anything.

Required:

- one system-level master plan;
- explicit repository roles;
- explicit authority boundaries;
- explicit development/release branch model;
- explicit evidence/certification ladder;
- explicit worker classes;
- explicit activation gates;
- explicit cross-repository correlation IDs.

**Current state:** PARTIAL → this document establishes the missing system-wide authority layer.

### I1 — Machine contracts

**Goal:** All autonomous communication uses versioned, bounded, machine-checkable contracts.

Required:

- worker packet schema;
- worker result schema;
- research request/evidence schemas;
- structured-data query/evidence schemas;
- capability inventory schema;
- evidence receipt format;
- stable identifiers.

**Current state:** SUBSTANTIALLY IMPLEMENTED in Automate.

The contracts exist, but the end-to-end system has not yet earned activation/certification.

### I2 — Automate development engine

**Goal:** Automate can autonomously decide what bounded capability work is eligible, construct a packet, validate the result, and prepare isolated repository changes.

Required:

- live capability/inventory inspection;
- bounded worker packet construction;
- fail-closed worker-result validation;
- isolated proposal application;
- stale-change protection;
- deterministic commit preparation;
- PR lifecycle support;
- readiness evaluation;
- autonomous-cycle orchestration;
- engine CI.

**Current state:** ACTIVE DEVELOPMENT.

The `engine` branch is the continuous development trunk. Development must not wait for every feature to reach `main`.

### I3 — Durable execution substrate

**Goal:** A worker job survives request termination and cannot be double-applied accidentally.

Required:

- durable job record;
- queue dispatch;
- lease ownership;
- heartbeat;
- timeout/deadline;
- stale-job recovery;
- retry/requeue;
- dead-letter handling;
- authenticated/bounded worker API;
- result persistence;
- correlation IDs.

**Current state:** PARTIAL.

Chanfana PR #3 contains most of the intended durable execution design, including D1 job state, queues, leases, recovery, and observability. Exact production resources and authoritative deployment evidence are still external gates.

The required queue resources are:

- `automate-worker-jobs`;
- `automate-worker-jobs-dlq`.

Repository code describing a resource is not proof that the real resource exists.

### I4 — Research and data acquisition substrate

**Goal:** External information can be acquired without becoming trusted merely because it came from a database, search engine, paper, or AI.

Required:

- bounded research request;
- bounded structured-data request;
- provider abstraction;
- source provenance;
- retrieval timestamps;
- content hashes;
- row/byte/time limits;
- evidence validation;
- source identity;
- independent-source comparison;
- rejection of malformed/unbounded provider output.

**Current state:** CONTRACTS READY, EXECUTION OFF.

A BigQuery worker is one possible provider. It is not “the research engine.” Search, scientific repositories, local datasets, SQL services, and other providers must fit the same evidence boundary.

### I5 — THE MIRROR scientific evidence layer

**Goal:** Interesting or uncertain claims can be investigated independently without contaminating Automate's authority.

Required:

- reproducible experiment identity;
- hypothesis/input/assumption capture;
- raw observations;
- numerical results;
- error and runtime measurements;
- stability/convergence analysis;
- perturbation testing;
- counterexample search;
- independent-route comparison;
- provenance chain;
- evidence handoff into Automate.

**Current state:** PARTIAL / HARDENING.

Mirror has substantial experimental infrastructure and provenance machinery. Its role is architecturally defined, but production/live validation and remaining hardening work still need completion. Mirror PRs that remain blocked by deployment/authentication evidence are not equivalent to certified infrastructure.

### I6 — End-to-end autonomous cycle

**Goal:** One complete bounded cycle works without a human manually stitching the repositories together.

Required path:

```
Automate capability frontier
 → worker/research packet
 → bounded execution
 → result/evidence
 → optional Mirror experiment
 → evidence normalization
 → Verification & Reconciliation Engine verification
 → verifiable packet
 → Automate authority review
 → isolated code proposal
 → tests
 → PR
 → reconciliation
```

No step may silently grant authority to the previous step.

**Current state:** NOT YET COMPLETE.

Automate contains the beginnings of this cycle, including `autonomous.py`, worker packet construction, result validation, publisher logic, and readiness evaluation. The cross-repository cycle is not yet proven end-to-end.

### I7 — Autonomous activation gates

**Goal:** Workers become active only after the system has earned the right to activate them.

The existing Automate readiness model requires all required gates to be true, including:

- worker contract tested;
- worker API authenticated and bounded;
- worker output independently validated;
- GitHub lifecycle exercised;
- live control plane clean;
- exact-head authority current;
- end-to-end dry run passed;
- autonomous foundation merged to main.

**Current state:** NOT READY.

This is intentional. “The code exists” is not the same as “the autonomous worker is safe to turn on.”

### I8 — Certified promotion pipeline

**Goal:** Continuous development on `engine` can become authoritative `main` without losing evidence.

Required:

- reviewable PR boundary;
- reconciliation;
- local tests;
- development CI;
- main merge;
- exact-head CI;
- Security Audit;
- independent cross-checks where required;
- certification bookkeeping.

**Current state:** PARTIAL / MANUAL.

The architecture is present, but the new `engine)-trunk model must be fully reconciled with promotion and certification bookkeeping.

### I9 — Autonomous capability discovery and expansion

**Goal:** The system stops depending on a human to enumerate every next capability.

Only after I0–I8 are sufficiently mature should the system autonomously:

- inspect the earliest incomplete capability frontier;
- research mature implementations and literature;
- identify missing mathematical primitives;
- propose reusable capability families;
- delegate isolated work;
- run numerical/experimental investigation;
- compare independent approaches;
- reject weak proposals;
- promote strong proposals;
- repeat.

**Current state:** FUTURE.

This is the long-term “engine develops new capabilities” milestone. It is not equivalent to turning on a generic coding agent today.

## 4. Worker classes and their boundaries

There are four conceptually different actors:

| Actor | Primary job | Can write code? | Can provide evidence? | Can certify? |
|---|---|---:|---:|---:|
| Automate primary engine | orchestration, verification, authority | Yes | Yes | Yes, subject to gates |
| Implementation worker | isolated capability implementation | Yes, bounded | Yes | No |
| Research/data worker | information/data acquisition | No direct authority writes | Yes | No |
| Mirror experiment worker | experiments/simulation/counterexamples | Experimental outputs only | Yes | No |

A worker can propose.

A worker cannot decide.

A research result can inform.

A research result cannot prove itself.

A Mirror experiment can falsify or support a hypothesis.

A Mirror experiment cannot certify Automate.

## 5. Cross-repository identity

When work crosses repository boundaries, preserve these identifiers whenever applicable:

- `action_cycle_id`;
- `capability_id`;
- `packet_id`;
- `job_id`;
- `result_id`;
- `request_id`;
- `experiment_id`;
- `run_id`;
- source/revision identifiers.

The identifiers form the audit trail connecting:

**why work was requested → what was executed → what was observed → what was changed → what was verified.**

Missing lineage must fail closed rather than being reconstructed from unrelated recent events.

## 6. Branch model

The repositories now use two conceptual branch classes:

### `engine`

Living development trunk.

- new capabilities;
- infrastructure work;
- reconciliation preparation;
- cross-repository integration;
- experiments;
- fixes.

It may move continuously.

### `main`

Certified release surface.

- only promoted work;
- exact-head verification applies;
- security evidence applies;
- certification claims may reference it.

A PR is a **promotion/review boundary**, not the place where all development must wait.

Feature branches may still be used for isolated delegated work, but they must eventually reconcile into `engine` before promotion to `main`.

This removes the previous ambiguity where every capability branch could accidentally become a development bottleneck.

## 7. Verification model

Use the strongest applicable evidence without collapsing different meanings:

```
PLANNED
  ↓
IMPLEMENTED
  ↓
LOCALLY_TESTED
  ↓
DEV_CI_VERIFIED
  ↓
MERGED_MAIN
  ↓
EXACT_HEAD_VERIFIED
  ↓
SECURITY_VERIFIED
  ↓
INDEPENDENTLY_CROSS_CHECKED
  ↓
CERTIFIED
```

The stages are not interchangeable.

In particular:

- implementation is not verification;
- CI on an old SHA is not CI on current main;
- Mirror agreement is not proof;
- research agreement is not proof;
- an external package result is not proof;
- a successful worker job is not proof;
- an AI assertion is not proof.

False negatives are preferred to unsupported positives.

## 8. Current infrastructure state

As of this review:

**Automate**
- Mathematical capability development: ACTIVE.
- `engine): ACTIVE development trunk.
- Worker contracts: substantially implemented.
- Research/data contracts: implemented.
- Autonomous-cycle code: implemented but not fully exercised end-to-end.
- Readiness gate system: implemented.
- External worker activation: OFF.
- Stage 1B improper integrals: ACTIVE capability frontier.
- Latest development commits must still earn fresh CI/security evidence.

**Chanfana Worker Substrate**
- `engine): active development trunk.
- Durable queue/lease/recovery design: substantially present in PR #3.
- Main release surface: not yet the authoritative autonomous worker deployment.
- Real queue/DLQ resources: NOT VERIFIED.
- External worker activation: OFF.

**THE MIRROR**
- `engine): active laboratory trunk.
- Experiment/provenance architecture: substantially present.
- Evidence handoff boundary: defined.
- Provenance fallback hardening: applied.
- Live production readiness: NOT CERTIFIED.
- Open hardening/deployment PRs remain evidence-gated.

## 9. Outstanding work, ordered by dependency

Do not attack these as a flat todo list. The dependency order is:

1. Keep the system map current.
2. Finish/harden the Automate development-engine control loop.
3. Finish the Stage 1B improper-integral capability while using the engine trunk.
4. Build independent Mirror cross-checks for convergence-sensitive mathematical claims.
5. Harden the research/data evidence path without enabling external execution.
6. Reconcile Chanfana durable execution into its release path and verify its actual runtime resources separately.
7. Prove an end-to-end dry-run across all repositories.
8. Close all autonomous-readiness gates.
9. Only then consider enabling an external implementation/research worker.
10. After activation is safe, expand autonomous capability discovery.

The system must not jump from “worker contracts exist” to “turn the worker on.”

## 10. What is NOT a dependency

These are explicitly not foundational dependencies:

- BigQuery;
- Ollama;
- a particular LLM provider;
- Cloudflare as a scientific authority;
- Vercel as a scientific authority;
- SymPy as mathematical authority;
- SciPy as mathematical authority;
- Lean as the only form of valid evidence;
- a particular search engine;
- any single external scientific dataset.

They are instruments or providers.

The contracts must remain provider-neutral.

## 11. Rules for future AIs

A new AI should read this document first.

Then:

1. inspect the current `engine) branch in all three repositories;
2. inspect the capability inventory and phase ledger;
3. inspect open PRs and outstanding verification evidence;
4. identify the earliest incomplete dependency;
5. do not duplicate an existing subsystem;
6. do not treat an open PR as authoritative;
7. do not treat `engine) as certified;
8. do not treat `main) as the development bottleneck;
9. preserve cross-repository identifiers;
10. fail closed when authority or lineage is unclear;
11. research existing mature implementations before substantial reimplementation;
12. use independent evidence when the capability needs it;
13. keep external workers OFF until readiness gates are genuinely satisfied;
14. update this master plan when an architectural assumption changes;
15. update the capability ledger when mathematical capability ordering/status changes.

The correct question is not “what file should I edit next?”

It is:

**“What dependency is currently preventing the system from safely advancing?”**

## 12. Immediate operating decision

The infrastructure audit does **not** invalidate the current Stage 1B work.

It clarifies its place.

The immediate development frontier remains:

**Stage 1B → improper integrals and convergence-aware handling**

while infrastructure work proceeds around it in parallel where it removes a real dependency.

The next infrastructure objective is not “build everything.”

It is:

**make the bounded Automate → worker/research → Mirror → evidence → verification → promotion cycle executable as a dry-run, while keeping external execution disabled.**

Once that cycle is mechanically proven, activation becomes a gate decision rather than a leap of faith.

---


## Cross-repository scientific division

The ecosystem is deliberately divided so capability development does not overload one repository:

- **Automate** is the scientific authority and reasoning/control plane. It owns canonical mathematics/physics capability definitions, verification, evidence interpretation, promotion, certification, and protected system records.
- **Chanfana** is the bounded execution substrate. It owns durable job delivery, leases, deadlines, heartbeats, retries/recovery, and execution envelopes. It does not interpret scientific meaning.
- **THE MIRROR** is the scientific frontier laboratory and external research instrument. It may investigate unusual mathematics/physics and acquire public external research evidence without requiring agreement with established theory. It owns observations, experiments, perturbations, anomaly classification, reproducibility, and research provenance. It does not certify scientific truth.
- **External research/data providers** are replaceable evidence sources. Provider output is never authority. Provider identity, request identity, retrieval time, revision/fingerprint where available, and limitations must travel with the evidence.

The intended flow is:

Automate request -> Chanfana bounded execution -> Mirror experiment/research -> raw observation/evidence -> Automate evaluation -> proposal -> verification -> promotion.

The three repositories may progress independently when dependencies permit. A blocked or queued subsystem must not stall unrelated capability work.

External research is deliberately broader than the implementation-worker role. Mirror may inspect public scholarly metadata, repositories, datasets/models, and other explicitly supported providers; this is a research capability, not a bypass around Automate's verification boundary.


## Laboratory operating contract — hardened 2026-10-06

THE MIRROR's existing laboratory instruments are first-class research capabilities. The external researcher and experiment workers may use them when they materially reduce uncertainty:

- perturbation laboratory;
- blinded controlled suites;
- projection/simulation suites;
- sandbox probes;
- experiment, prediction, observation, and evidence ledgers;
- anomaly/new-science classification.

The rule is **instrument selection by research need, not continuous activity**. Research when outside evidence can clarify an idea, perturb when sensitivity or falsification matters, simulate when model comparison is useful, and stop when evidence is insufficient or the question is answered.

Mirror may generate candidate mathematics, physics, alternative models, anomalies, counterexamples, and proposed experiments. Those outputs remain observations/proposals until Automate independently evaluates them. Established mathematics and physics are comparison baselines, not mandatory conclusions for Mirror's frontier laboratory.

The hardened loop is:

```
Automate capability frontier / research question
        ↓
Chanfana bounded job envelope
        ↓
Mirror researcher selects the least-powerful useful instrument
        ├── world research
        ├── perturbation
        ├── simulation
        ├── controlled/blinded experiment
        └── sandbox / observation tools
        ↓
raw observation + provenance + experiment/run identity
        ↓
Automate evidence normalization and independent verification
        ↓
candidate capability / anomaly / refutation / new hypothesis
        ↓
mathematical + numerical + independent checks
        ↓
proposal / PR / reconciliation
```

No Mirror instrument may mutate Automate authority records, and no external source may self-certify. The researcher is expected to use the laboratory when needed, not manufacture an endless stream of weak evidence merely because the system can call a tool.


---

# Architecture upgrade — Verification & Reconciliation Engine

**Effective design decision: 2026-10-07**

The system is now explicitly divided into four logical compartments:

1. **Automate** — scientific authority, capability frontier, canonical semantics, final integration and certification authority.
2. **Chanfana** — durable bounded execution and transport substrate.
3. **Verification & Reconciliation Engine** — a bounded verification/reconciliation machine hosted on Chanfana. It has no independent scientific authority.
4. **THE MIRROR** — experimental mathematics/physics laboratory and research instrument.

The Verification Engine is a logical subsystem hosted by Chanfana, not a fifth authority and not a replacement for Automate.

## Permanent loop

```
AUTOMATE
  capability frontier / bounded request
        ↓
CHANFANA
  durable job / lease / resource boundary
        ↓
VERIFICATION & RECONCILIATION ENGINE
  inventory
  reconcile
  repair safely
  test
  CI / Security
  mathematical verification
  alternate-route / counterexample checks
  evidence assembly
        ↓
VERIFIABLE PACKET
        ↓
AUTOMATE
  accept/integrate
  reject
  quarantine
  request more evidence
        ↓
next frontier
        ↓
repeat forever
```

When the verification backlog is genuinely cleared, the Verification Engine may request laboratory work from Mirror through Chanfana. The engine does not contain the laboratory and cannot replace it.

## Authority boundary

The Verification Engine may say:

> The configured evidence checks passed for this exact candidate revision.

It may never say:

> Automate must accept this capability.

Only Automate can decide whether a capability becomes authoritative, advances the phase ledger, enters the authoritative inventory, or is certified.

The engine therefore has a permanent operational role but no permanent sovereignty. Its output is always evidence packaged for Automate.

## Engine components

The engine should reuse the machinery already present across the three repositories rather than create parallel infrastructure:

- **Intake/provenance:** package identity, source revisions, hashes and lineage.
- **Repository inventory:** branches, PRs, commits, files and dependencies.
- **Reconciliation planner:** ordering, conflicts, stale work and ownership.
- **Repair controller:** isolated bounded patches with protected paths and retry budgets.
- **Deterministic verification kernel:** schemas, contracts, tests, static checks and security checks.
- **Mathematical verification fabric:** symbolic, formal, numerical, dimensional/structural, alternate derivation, independent implementation and counterexample checks where applicable.
- **CI controller:** dispatch/polling plus exact-SHA binding.
- **Evidence graph/receipt store:** immutable provenance of what was checked and how.
- **Evidence-state machine:** records verification progress but does not self-certify.
- **Promotion packet builder:** produces the verifiable packet consumed by Automate.
- **Escalation/quarantine:** unresolved or unsafe cases stop rather than being forced through.

LLM/agentic components may assist diagnosis, review, research interpretation or repair proposals. Deterministic execution and recorded evidence remain the evidence base.

## Theory-neutral verification

Verification must be **theory-neutral**, not a known-physics conformity oracle.

For established claims, established mathematics and physics can provide strong verification targets, reference implementations, limiting cases and controls.

For novel claims, the engine instead asks whether the claim is internally coherent and whether independent evidence supports, contradicts, or fails to resolve it. It may use:

- symbolic equivalence;
- formal proof where applicable;
- numerical evaluation;
- precision/resolution changes;
- perturbation;
- invariant/residual checks;
- alternate derivation;
- independent implementation;
- counterexample search;
- reproducibility;
- assumption and domain analysis.

Valid outcomes include supported, reproduced, consistent, contradicted, false and **unresolved**.

Disagreement with established physics is not automatically failure and is not automatically proof of new science. The system must first distinguish implementation defects, numerical artifacts, assumption mismatch, convention/coordinate differences, solver limitations and genuine model disagreement.

“Independent evidence” means an alternative evidence route, not conformity with scientific canon.

## Controlled repair

The engine may repair implementation defects, but every repair is evidence-producing and bounded:

```
failure
  → diagnose
  → propose smallest safe repair
  → apply isolated repair
  → preserve or strengthen tests
  → rerun
  → record lineage
```

Forbidden:

```
test fails
  → weaken/delete test
  → pass
  → certify
```

Protected tests, security gates, authority records and evidence requirements cannot be weakened merely to clear the queue.

## Verification lifecycle

The engine should maintain:

```
RECEIVED
 → INVENTORIED
 → RECONCILIATION_PLANNED
 → RECONCILED
 → LOCALLY_VERIFIED
 → DEV_CI_VERIFIED
 → MERGE_CANDIDATE
 → MERGED_MAIN
 → EXACT_HEAD_VERIFIED
 → SECURITY_VERIFIED
 → MATHEMATICAL_EVIDENCE_COMPLETE
 → VERIFIABLE_PACKET_READY
 → AUTOMATE_REVIEW
    ├─ ACCEPT / INTEGRATE
    ├─ REJECT
    ├─ QUARANTINE
    └─ REQUEST_MORE_EVIDENCE
```

This is a multidimensional evidence state, not a single “proof score”.

## Verifiable packet

The engine's principal output is a versioned, provenance-preserving packet bound to:

- action-cycle, capability, packet, job and result identifiers;
- exact repository commit/tree information;
- branch/PR/merge identifiers;
- changed-file hashes;
- test commands and results;
- CI and Security Audit run identifiers;
- verifier build/version and rule-set version/hash;
- mathematical evidence, assumptions and tolerances;
- Mirror experiment identifiers when used;
- external source identifiers when used;
- repair history;
- unresolved issues and limitations.

The packet answers:

**What exactly was checked, against which exact revision, using which machinery, under what assumptions, and what remains unknown?**

The packet is evidence, not an instruction to accept.

## Backlog-first acceptance

The engine must be tested against the real existing verification backlog, not a toy repository.

Its first package should contain the relevant Stage 1A–3A history, current Automate state, historical PR/branch revisions, capability/dependency metadata, useful implementation files, tests, documentation, known defects, provenance, existing evidence receipts and conflicts.

Processing is:

```
inventory
 → dependency graph
 → reconcile
 → bounded repair
 → tests
 → CI / security
 → mathematical verification
 → alternate/counterexample checks
 → exact-head evidence
 → verifiable packet
 → Automate decision
```

Historical PR descriptions, branch names, AI claims and expected outputs remain untrusted. Useful code may be harvested; authority may not.

This backlog is the first real workload and the acceptance test for the Verification Engine.

## Chanfana integration

The existing Chanfana machinery already supplies the right substrate:

- durable job records;
- queue dispatch;
- leases;
- heartbeats;
- stale-job recovery;
- retries/requeue;
- authenticated worker endpoints;
- bounded execution;
- structured packet/result transport.

The Verification Engine should become a specialized job family on top of those primitives, including reconciliation, verification, repair, CI-wait, mathematical-check, Mirror-request, evidence-assembly and promotion-packet jobs.

Chanfana transports and bounds the work. It does not decide scientific meaning.

## Mirror boundary

**Open-ended autonomous discovery remains governed by operating mode. Mirror's engineering, research, diagnosis, repair, capability-generation, and bounded verification work is available during backlog clearing.**

After backlog clearance and readiness gates, the Verification Engine may commission Mirror when an evidence question genuinely requires laboratory work:

```
Verification Engine
   ↓
Chanfana bounded Mirror request
   ↓
Mirror laboratory
   ↓
raw observation + provenance
   ↓
Chanfana
   ↓
Verification Engine
   ↓
verifiable packet
   ↓
Automate decision
```

The engine never receives Mirror's laboratory authority. Mirror never receives verification authority.

This is deliberate: the laboratory must remain free to investigate unusual mathematics and physics without being forced to conform to the verifier's existing knowledge.

## Continuous operating contract

Once the backlog is cleared, the Verification Engine does not become idle and does not become the boss.

The permanent cycle is:

**Automate selects the frontier → Chanfana bounds transport → Verification Engine reconciles and verifies → Mirror investigates when needed → Verification Engine produces a verifiable packet → Automate decides → frontier advances → repeat indefinitely.**

No final capability count is assumed.

The Verification Engine is permanent machinery. Automate remains the sovereign authority.


## Reconciled architecture: Verification & Reconciliation Engine is a distributed logical subsystem

The Verification & Reconciliation Engine is **not a fourth repository and not a monolithic machine that belongs entirely to Chanfana**. It is a logical subsystem assembled from capabilities already present across the three repositories.

Its job is to answer two questions: what is wrong, inconsistent, unsupported, or insufficiently evidenced, and what is the smallest justified correction or additional evidence needed to resolve it?

It may diagnose and repair implementation, contract, numerical, data, provenance, test, CI, or integration mistakes under bounded repair policy. It must preserve the possibility that the apparent failure is actually a bad test, incomplete assumption, numerical artifact, backend mismatch, or genuinely unresolved scientific behavior. It must never weaken evidence merely to make a backlog item pass.

### Distributed ownership

```
                 AUTOMATE
      canonical mathematics / physics
       rules + backends + contracts
                  │
                  │ evidence requests / canonical checks
                  ▼
        VERIFICATION & RECONCILIATION ENGINE
        logical subsystem spanning the repos
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   CHANFANA              THE MIRROR
 durable execution       scientific laboratory
 queues / leases         models / simulations
 recovery / auth         perturbations / sweeps
 provenance / packets    numerical diagnostics
 repair-job control      counterexamples / discovery
 CI orchestration        experimental evidence
        │                   │
        └─────────┬─────────┘
                  ▼
          verifiable packet
                  │
                  ▼
               AUTOMATE
          authority / promotion
```

Chanfana is therefore an **internal substrate of the verifier**, not an external peer dependency. Mirror is a **scientific execution compartment of the verifier when laboratory work is required**, not merely a passive evidence mailbox. Automate supplies canonical semantics and remains the final authority.

### Compartments that may be shared

The repositories may jointly implement the verifier where separation would create needless duplication. Shared compartments include:

- versioned job and packet contracts;
- correlation IDs and provenance lineage;
- evidence normalization and receipt formats;
- bounded execution policies;
- repair-request and repair-result contracts;
- diagnostics and failure-classification vocabulary;
- experiment request/result envelopes;
- CI/security evidence collection interfaces;
- verifiable-packet assembly;
- provider-neutral research/data envelopes.

Shared means **compatible ownership with one contract**, not duplicated competing implementations. Every shared capability still has one implementation owner or an explicit split of responsibility.

### Strict ownership boundaries

- Automate owns canonical scientific semantics, capability order, inventory, authoritative contracts, acceptance policy, Git promotion, and certification.
- Chanfana owns durable execution/control-plane mechanics: jobs, queues, leases, heartbeats, recovery, authentication, resource bounds, transport, and persistence of execution/evidence state.
- Mirror owns laboratory mechanics: hypothesis execution, simulation, perturbation, numerical experimentation, discovery analysis, counterexample search, and experimental provenance.
- The Verification Engine owns the **reasoning workflow** that connects these capabilities: inventory, diagnosis, evidence selection, repair planning, bounded repair, independent checks, CI interpretation, and packet construction. Its authority is limited to producing evidence and verifiable packets.

### Backlog-clearing role of Mirror

The current verification backlog is not required to be cleared by Chanfana alone. Chanfana makes work durable and bounded; Mirror can perform substantial scientific investigation and numerical cross-checking; Automate provides canonical mathematical checks and the authority boundary. The verifier coordinates the appropriate combination.

During the current Stage 1A–3A reconciliation period, Mirror/external-world research remains **ON HOLD as an autonomous discovery source**, but Mirror's existing local scientific machinery may be used in tightly bounded verification work when needed and explicitly authorized by the current activation policy. This prevents the laboratory from being needlessly idle while still preventing uncontrolled discovery from contaminating the backlog.

### Repair rule

```
failure
  → classify
  → diagnose cause
  → determine whether implementation/test/contract/assumption/data/numerics is responsible
  → propose smallest safe repair
  → apply in isolation
  → preserve or strengthen evidence
  → rerun focused checks
  → assemble lineage
```

Forbidden:

```
failure → weaken/delete evidence → pass → certify
```

### Permanent cycle

```
Automate frontier/request
  → Verification Engine intake
  → Chanfana durable job
  → deterministic checks and/or Mirror scientific work
  → diagnosis / bounded repair
  → independent evidence
  → verifiable packet
  → Automate authority decision
  → next frontier
  → repeat
```

The loop may run indefinitely. The verifier never becomes the authority simply because it has become good at verification.


## 10. Operating modes and the long-term closed loop

The autonomous system does not run every loop all the time.

### BACKLOG mode — canonical curriculum dominant

While the phase/capability ledger contains unresolved canonical work, the control plane remains in BACKLOG mode.

In BACKLOG mode:

- the strict earliest-ready ledger gate selects the next capability;
- implementation workers may be commissioned through bounded packets;
- the Verification & Reconciliation Engine may investigate, test, diagnose, repair, and reconcile;
- THE MIRROR may research, code, implement, repair, simulate, challenge, and verify the active capability when useful;
- open-ended discovery and new capability proposals remain governed by the current operating mode;
- Mirror discovery cannot directly create new authoritative capability scope.

The purpose is to use the 1A–13A backlog as the system's proving ground. Every completed capability exercises the same queue, worker, transport, evidence, verification, reconciliation, learning, and promotion machinery.

### DISCOVERY_READY mode — canonical curriculum exhausted

When the canonical queue reaches a terminal state with no unresolved pre-discovery work, the control plane may expose DISCOVERY_READY.

This does not mean a new capability is automatically correct or admitted.

It means the discovery loop is now permitted to operate.

THE MIRROR may:

1. inspect its accumulated experiments, observations, research notes, and previous candidate history;
2. choose a bounded mathematical or physical question;
3. research established and competing approaches;
4. run available bounded laboratory tests;
5. search for counterexamples, instability, missing assumptions, and alternative explanations;
6. create at most one candidate capability proposal per bounded discovery cycle;
7. hand the candidate to Chanfana as untrusted durable evidence.

Automate then:

1. validates the proposal contract;
2. checks collisions and dependency/prerequisite state;
3. creates a non-authoritative future-capability record;
4. sends the candidate through bounded investigation and Verification & Reconciliation;
5. compares independent evidence where required;
6. determines implementation scope and regression obligations;
7. opens a normal implementation/reconciliation PR;
8. only after the ordinary verification/promotion lifecycle succeeds, admits the capability into the authoritative capability inventory and ledger.

The future-capability record is therefore a staging area between discovery and canonical curriculum. Mirror never appends directly to the authoritative ledger.

### Investigation is bidirectional

After DISCOVERY_READY, Mirror has two legitimate directions of use:

**Automate → Mirror:** Automate requests experiments when mathematical or physical uncertainty needs laboratory evidence, perturbation, simulation, or counterexample search.

**Mirror → Automate:** Mirror independently discovers research questions, candidate methods, or candidate capabilities and submits them for triage.

The two directions share evidence contracts but never share certification authority.

### Learning closes the behavioral loop

Experiences from backlog execution and post-ledger discovery feed the same learning machinery.

Repeated successful strategies remain candidates until independently reproduced.

Repeated failures create investigation candidates.

Adopted lessons may change future strategy selection.

System-improvement lessons may produce bounded mutable evolution proposals.

Constitutional/epistemic rules remain outside automatic promotion.

The long-term loop is therefore:

Canonical capability frontier
→ bounded implementation
→ durable execution
→ evidence / Mirror investigation
→ Verification & Reconciliation
→ reviewable promotion
→ learned experience
→ next canonical frontier

and, after canonical exhaustion:

Canonical queue exhausted
→ Mirror discovery
→ research + experiment + challenge
→ candidate capability
→ Automate triage
→ verification / implementation
→ explicit ledger admission
→ next canonical frontier.

This is a controlled expansion loop, not an unconstrained self-rewriting loop.

<!-- Control-plane release audit marker: 2026-10-07. No behavioral change. -->


## Frontier worker toolbelt and scientific grounding policy

THE MIRROR is now treated as the frontier scientific AI worker, not merely a research endpoint. Its bounded toolbelt includes scholarly/code research, repository workspace inspection and writing, local execution, isolated Git proposal preparation, experiment execution, descriptive analysis, provenance capture, and provider-neutral AI decision making.

Research providers are ordered so established/reference grounding comes first: OpenAlex, Crossref, INSPIRE-HEP, Semantic Scholar, then arXiv and code/model sources. A trusted index or repository is not itself proof that a returned claim is established physics. Reference grounding means locating mature methods, canonical mathematics/physics, known failure modes, and independent implementations before implementing a capability or elevating a frontier claim.

The policy is deliberately asymmetric:

- established/reference capability work is preferred before frontier invention;
- repair takes precedence over all discovery;
- current backlog takes precedence over ledger expansion;
- discovery is allowed only when explicitly granted;
- disagreement with established physics is investigated rather than automatically rejected;
- lack of reference grounding blocks non-repair frontier implementation;
- no worker can certify its own result.

The concrete cross-repository path is:

Automate mission -> Chanfana `mirror.frontier_job.v1` -> Mirror frontier AI -> bounded research/code/experiment tools -> evidence/provenance -> Automate verification -> proposal/promotion.

Chanfana remains the durable transport and memory substrate. Mirror may modify its bounded workspace and create reviewable branches/PRs for its own work or proposed cross-repository changes. Direct unreviewed mutation of Automate authority surfaces remains forbidden.
