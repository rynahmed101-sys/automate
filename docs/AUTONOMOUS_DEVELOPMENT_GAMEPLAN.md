# Autonomous Development Game Plan

## Purpose

Automate should advance continuously without confusing speed with authority.

The operating model is:

OBSERVE -> PLAN -> PREPARE -> WORK -> INSPECT -> TEST -> RECONCILE -> VERIFY -> CERTIFY -> ADVANCE

A slow worker, a queued CI run, or an unavailable external worker is not itself a reason for Automate to stop. When a lane is waiting, Automate should perform other safe work that does not cross an evidence boundary.

## Boss boundary

The "boss" is the deterministic Automate control plane. AI workers are reasoning labor, not authority.

The boss owns:
- roadmap order and phase gates;
- capability ownership and collision detection;
- allowed/forbidden file boundaries;
- proposal validation;
- independent tests and evidence;
- Git branch/PR lifecycle;
- merge and certification decisions;
- retries, recovery, and stop conditions;
- the durable record of what is known versus merely claimed.

Workers may propose implementation. They may not promote their own trust level.

## Work lanes

Automate should reason in independent lanes so waiting does not become idleness:

1. Capability lane: implement the earliest legitimate mathematical/physics capability.
2. Verification lane: inspect tests, adversarial cases, cross-checks, and evidence quality.
3. Reconciliation lane: repair stale branches, inventory drift, duplicate ownership, and control-plane defects.
4. Research lane: inspect mature external mathematics/physics implementations and extract patterns, not authority.
5. Infrastructure lane: improve worker contracts, evidence receipts, scheduling, recovery, and machine-agent interfaces.
6. CI lane: diagnose failures and improve feedback speed without weakening authoritative verification.

A lane may proceed only when its changes are independent of blocked or unverified work.

## Speed policy

- Do not wait for a worker merely because a worker was expected to do the next task.
- Do not wait for a CI run merely because CI is running.
- Do not start later mathematical capabilities merely because they look interesting.
- Do parallel preparation and control-plane work while the earliest capability is blocked.
- Never trade away exact-head verification, security checks, branch boundaries, or fail-closed behavior for speed.
- Prefer small, reviewable changes that can be verified independently.
- If full CI is resource-bound, improve the feedback path by sharding or isolating expensive tests. Never delete or weaken authoritative coverage.

## Evidence model

Every meaningful autonomous action should be representable as an evidence receipt containing, where applicable:
- action/cycle identifier;
- exact repository and base SHA;
- capability or control-plane target;
- packet/result identifiers;
- changed-file hashes;
- focused test command and result;
- independent verification result;
- CI/security run identifiers and conclusions;
- resulting branch/PR/merge SHA;
- trust state;
- unresolved issues;
- timestamp.

Trust states are distinct:
PLANNED -> IMPLEMENTED -> LOCALLY_TESTED -> DEV_CI_VERIFIED -> MERGED_MAIN -> EXACT_HEAD_VERIFIED -> SECURITY_VERIFIED -> INDEPENDENTLY_CROSS_CHECKED -> CERTIFIED

No lower-trust evidence may masquerade as a higher-trust state.

## Research policy

External repositories, papers, datasets, examples, and AI-generated research are evidence sources, not authorities.

Useful research is converted into:
- a concrete reusable capability requirement;
- an adapter/backend boundary;
- a test or counterexample;
- a provenance record;
- or a design pattern.

Do not import a dependency merely because it solved a related problem.

## Recovery policy

When work fails:
1. classify the failure;
2. preserve the evidence;
3. minimize the failing surface;
4. retry only if the failure class permits it;
5. repair the smallest responsible layer;
6. rerun focused evidence;
7. return to authoritative verification.

Examples:
- transient runner interruption -> rerun;
- resource exhaustion -> isolate/shard expensive tests;
- assertion failure -> repair code/tests;
- scope violation -> reject proposal;
- stale branch -> rebuild from current authoritative base;
- unsupported semantics -> return UNKNOWN, do not guess.

## Advancement rule

After each completed action, Automate recomputes the next safe action from:
- the phase ledger;
- live Git state;
- capability inventory;
- active branches/PRs;
- evidence receipts;
- current verification state.

The next action is not chosen from memory, worker enthusiasm, or an old branch.

## Immediate implementation sequence

W0: finish the autonomous contract foundation without enabling live workers.
W1-W2: harden the machine worker API and provider-neutral model boundary.
W3: make repository context packet-authorized and provenance-preserving.
W4-W5: make proposal application and PR lifecycle independently testable.
W6: build reconciliation/recovery as a first-class supervisor function.
W7: support bounded one-capability-at-a-time autonomous cycles.
W8: add controlled self-healing.

In parallel, continue mathematical development only at the earliest legitimate ledger frontier:
Stage 1B improper integrals and convergence-aware handling.

## Activation rule

A real external capability worker remains OFF until all readiness gates are backed by independent evidence. A dry run is not a merge. A worker result is not proof. A green PR run is not exact-head certification.

Once activation is earned, the system may launch one bounded capability at a time and continue other safe lanes while that capability is waiting.

## Definition of "continuous"

Continuous does not mean uncontrolled.

It means that whenever one lane is blocked, another safe lane is selected automatically. The system should stop only when no safe action remains, an authority boundary requires human judgment, or a failure requires escalation.
