# Autonomous Scientific System Master Plan

**Status:** AUTHORITATIVE SYSTEM MAP  
**Owner:** Automate primary integrator  
**Scope:** Automate + Chanfana Worker Substrate + THE MIRROR + external research/data workers  
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
Automate independently evaluates the evidence
      ↓
Automate verifies the mathematical/physical claim
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

## Current live operating mode - 2026-10-08

The system operates as a bounded autonomous development system. Automate owns the ledger, authority, verification, promotion, and certification decisions. Chanfana owns bounded execution and durable job state. Mirror is a non-deployed laboratory and research/engineering partner. The three repositories follow the capability ledger in Automate; later-stage work may be preserved but cannot advance the active frontier.

The autonomous control plane may make operational decisions such as capability selection, research commissioning, retry, quarantine, repair generation, reconciliation, promotion, and bookkeeping. It may not rewrite the ledger's authority model, self-certify evidence, weaken verification gates, or silently promote out-of-order capabilities.

## 2. Repository roles

### Automate — authority and scientific reasoning engine

Automate owns:

- canonical mathematical and physics semantics;
- capability representation and rule registry;
- mathematical verification backends;
- capability inventory;
- phase/capability ordering;
- worker packet and result contracts;
- research/data request and evidence contracts;
- autonomous-cycle orchestration;
- readiness gates;
- evidence receipts;
- Git proposal/promotion logic;
- certification state.

Automate is the only repository allowed to decide that a capability is verified/certified.

Its `engine` branch is the living development trunk.

Its `main` branch is the certified release surface.

### Chanfana Worker Substrate — bounded execution infrastructure + system memory

`rynahmed101-sys/chanfana-openapi-template` executes bounded jobs reliably and persists durable system memory for Automate and Mirror.

It owns:

- durable job persistence;
- queue dispatch;
- execution leases;
- heartbeats;
- stale-job recovery;
- retry/requeue behavior;
- worker API boundaries;
- runtime resource/time limits;
- structured job/result transport.

It does **not** own:

- mathematical truth;
- the Automate capability ledger;
- capability certification;
- Git authority;
- scientific interpretation.

Its `engine` branch is the living infrastructure development trunk.

Its `main` branch is the release surface.

### THE MIRROR — autonomous engineering partner + experimental scientific laboratory

`rynahmed101-sys/the-mirror` is the system's persistent AI engineering and scientific environment. It may perform research, diagnosis, implementation, repair, capability generation, experiments, simulation, perturbation, counterexample search, coding, and bounded verification work.

Mirror may prepare reviewable changes against Automate's exact frontier revision, but it cannot self-certify, rewrite Automate authority, or bypass CI, verification, or promotion gates. It supplies work and evidence; Automate decides whether that work counts.

It owns:

- hypotheses;
- controlled experiments;
- simulations;
- perturbations;
- counterexample searches;
- numerical comparison;
- runtime/error/stability observations;
- reproducible experiment provenance;
- experimental evidence.

Mirror observations are evidence to Automate, not Automate truth.

Mirror must never mutate Automate's ledger, inventory, rule registry, certification state, or Git history.

Its `engine` branch is the living laboratory development trunk.

Its `main` branch is the release surface.

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

**Current state:** ACTIVE LABORATORY.

Mirror is a non-deployed scientific and engineering laboratory. It can produce hypotheses, experiments, simulations, counterexamples, and evidence packets. Automate treats all Mirror output as untrusted evidence and independently decides whether it matters. No deployment gate is attached to Mirror.

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
 → Automate independent verification
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

The immediate development frontier remains the earliest incomplete Stage 1B capability after the completed series-expansion milestone:

**Stage 1B → partial derivatives and total differentials**

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


## Self-developing capability loop — permanent contract

Automate is not intended to depend on humans supplying capability PRs. The capability ledger is a living frontier: Automate identifies the earliest dependency-ready missing capability, commissions external research through Chanfana, and gives the resulting untrusted evidence to the implementation worker. Mirror is the external researcher and laboratory; Chanfana transports and bounds the work; Automate remains the evaluator and release authority.

The loop is continuous:

1. inspect the capability frontier;
2. commission Mirror to research mature approaches, contradictions, counterexamples, prerequisites, and unconventional alternatives;
3. use Mirror's laboratory instruments when research alone cannot resolve the question;
4. feed bounded evidence into capability implementation;
5. test, cross-check, reconcile, and verify;
6. promote only after the existing verification ladder succeeds;
7. re-read the frontier and continue with the next capability.

This loop must not assume a final capability count. New capabilities discovered by research or laboratory work may become proposals for the ledger after independent evaluation. Novelty is a candidate outcome, never an automatic promotion. The system is therefore designed to keep developing as the mathematical/physical frontier expands rather than reaching a fixed “finished” state.
