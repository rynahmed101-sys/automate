# Automate Autonomous Worker Program

## Purpose
Turn Automate's existing development control plane into a bounded autonomous software-development system.

Target loop:
OBSERVE -> determine earliest legitimate capability -> construct work packet -> send to isolated worker -> worker proposes/implements -> Automate independently inspects -> focused tests/control-plane checks -> reconcile -> authoritative verification -> update state -> next capability.

The worker is never authoritative. GitHub state, deterministic control-plane logic, tests, and authoritative verification remain the sources of truth.

## Architecture

### Automate: supervisor and judge
Automate owns roadmap ordering, dependency state, worker packet construction, allowed/forbidden file boundaries, reconciliation, verification/certification bookkeeping, merge decisions, retries, and stop conditions.

### Worker: implementation actor
The worker reads its packet, retrieves permitted context, uses a replaceable AI model, produces bounded changes, runs local checks, and may later open an isolated capability PR when explicitly authorized.

Worker output is an attempted action, not proof.

### Chanfana/Cloudflare worker substrate
Use `rynahmed101-sys/chanfana-openapi-template` as the machine-facing Worker reference:
- Hono
- Chanfana OpenAPI 3.1
- Zod validation
- Cloudflare Worker runtime
- D1 durable job state
- Vitest Workers-pool tests

Adapt only after the Automate contract is stable.

### THE MIRROR
Keep Mirror as an optional laboratory for model experiments, sandboxing, independent evidence, and research. Mirror does not become authority over Automate's repository state.

## Provider strategy
Ollama is optional, not foundational. The worker contract is provider-neutral. The first Cloudflare implementation may use native Workers AI; another provider can be substituted later. Contract tests must work without a model.

## Safety boundary
The autonomous worker may not modify the ledger, capability inventory, verification evidence, CI/security workflows, shared integration surfaces, or arbitrary files; bypass guards; claim certification; delete files; or merge its own work.

High-risk, destructive, cross-stage, architectural, credential, workflow, and security changes remain human-gated until separately trusted.

## Build stages

### W0 — contract foundation
Status: IN PROGRESS
- worker packet/result schema
- deterministic packet builder
- result validator
- CLI rendering
- tests
- durable plan

### W1 — machine worker API
Build from the Chanfana template:
- health
- bounded packet submission
- execution request
- job status/result
- authentication
- idempotency
- explicit limits

No GitHub mutation initially.

### W2 — model adapter
Provider-neutral interface with deterministic mock and Cloudflare Workers AI implementation. Model output remains untrusted.

### W3 — repository context
Worker reads packet-authorized files, tests, capability docs, and exact base commit. Authorization is derived from the packet, never from model prose.

### W4 — proposal application
Automate independently applies allowed worker changes to an isolated branch.

### W5 — PR lifecycle
Add branch/PR creation, CI observation, retry, and stop-on-violation behavior.

### W6 — reconciliation supervisor
Automate resolves stale branches, duplicate ownership, collisions, ordering, and bookkeeping.

### W7 — autonomous capability loop
Bounded one-capability-at-a-time loop: select -> launch -> monitor -> validate -> reconcile -> verify -> merge -> ledger -> next.

### W8 — controlled self-healing
Permit bounded repair/retry of worker failures without silently upgrading verification state.

## Worker readiness gate
Secondary AI workers remain OFF until:
1. contract is implemented and tested;
2. API authentication and bounded execution exist;
3. worker output is independently validated;
4. GitHub branch/PR lifecycle is safely exercised;
5. live control-plane audit passes;
6. exact-head verification remains authoritative;
7. an end-to-end dry run succeeds without a real merge.

Only then is the first real worker considered ready.

## Current mathematical frontier
Stage 1B improper integrals and convergence-aware handling (Issue #115) remains the next capability. Worker infrastructure must not leapfrog the ledger.

## Design principle
The system should make routine development increasingly automatic, while preserving human judgment for decisions that require earned trust.

Automation earns authority one verified boundary at a time.
