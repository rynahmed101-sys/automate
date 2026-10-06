# Self-Improvement and Self-Evolution Architecture

**Status:** foundation under development  
**Authority:** subordinate to `docs/AUTONOMOUS_SYSTEM_MASTER_PLAN.md`  
**Principle:** Automate learns from evidence without allowing learned content to silently rewrite authority.

## 1. The learning loop

The mature loop is:

```
ACT
 ↓
OBSERVE
 ↓
RECORD EXPERIENCE
 ↓
COMPARE WITH HISTORY
 ↓
GENERATE CANDIDATE LESSON
 ↓
REPRODUCE
 ↓
GENERALIZE / ATTACK
 ↓
INDEPENDENT VERIFICATION
 ↓
PROMOTE LESSON
 ↓
CHANGE FUTURE DECISION POLICY
 ↓
ACT AGAIN
```

A system that only records outputs is not self-improving. Improvement requires that future behavior changes because of verified prior experience.

## 2. Memory classes

The foundation stores several logically different objects:

- experiences: what happened during a bounded action cycle;
- lessons: hypotheses extracted from multiple or important experiences;
- strategy evidence: accumulated success/failure history used to rank strategies conservatively;
- system-evolution proposals: reviewable requests to change reusable machinery.

Scientific observations remain evidence, not authority. A lesson never becomes adopted merely because an AI generated convincing prose.

## 3. Lesson lifecycle

```
CANDIDATE
  ↓
REPRODUCED
  ↓
VERIFIED
  ↓
ADOPTED
```

Alternative terminal paths are `REJECTED`, `UNKNOWN`, or `CONTEXT_BOUND`. Adopted lessons can later become `SUPERSEDED`.

The foundation requires explicit verification evidence for VERIFIED/ADOPTED transitions and requires an explicitly independent evidence marker for adoption.

## 4. Strategy learning

The first implementation does not pretend to understand causality automatically.

It records which strategy was used and whether the bounded action produced success, failure, contradiction, or unknown. Strategy recommendations use a conservative Wilson lower bound rather than raw success rate. This means a strategy with one lucky success is not allowed to outrank a repeatedly tested strategy without qualification.

Future work can add richer causal analysis while retaining the same evidence boundary.
Raw experience is never sufficient to change autonomous strategy. A strategy override requires an explicitly adopted lesson and enough conservative historical evidence to clear the configured threshold.

## 5. Self-evolution

System-evolution proposals are distinct from ordinary lessons.

Mutable classes include:

- new reusable capabilities;
- new verification methods;
- strategy changes;
- scientific knowledge representations.

Constitutional proposals include changes to the deepest epistemic/authority layer. They are never auto-promotable.

This prevents the recursive failure mode where the system changes the rules that judge whether changing the rules was legitimate.

## 6. Three-repository loop

Automate owns the learning ledger and promotion decision.

Chanfana owns durable execution history and transports experience/evidence across service boundaries.

THE MIRROR supplies experiments, perturbations, counterexamples, and unusual/scientific observations that can challenge lessons and system-evolution hypotheses.

The Verification & Reconciliation Engine independently tests lessons and evolution proposals. Automate remains the final authority for repository state, but not a permanently fixed authority over scientific conclusions.

## 7. Reversible system evolution

A verified/adopted improvement can eventually target mutable Automate machinery. The current foundation intentionally stops one step before application:

1. an evolution proposal is created;
2. evidence and regression obligations are reviewed;
3. the proposal reaches ADOPTED only through the normal verification boundary;
4. an exact base revision is captured;
5. a bounded proposal-only change plan is generated;
6. the existing worker/PR/reconciliation/exact-head/security lifecycle applies the actual repository change;
7. the resulting system version is evaluated against the same historical and newly generated regression corpus;
8. failed evolution is rolled back or superseded rather than silently retained.

The system must never use its own newly proposed behavior as the sole proof that its behavior is safe.

## 8. Current boundary and remaining work

The foundation now has bounded experience emission in the autonomous cycle when a learning database is supplied. Repeated failures can become candidate lessons, repeated successes can become candidate strategy lessons, historical failures can become regression obligations, and only ADOPTED strategy lessons may override the default strategy.

Remaining work is to make learning storage a durable cross-cycle service, ingest worker/Mirror verification evidence automatically, synthesize regression suites from important failures, connect learned lessons to more worker decisions, and build the reversible mutable-machinery evolution path.

Those stages must be built incrementally and tested like any other capability.


## 9. Self-evolution execution boundary

The repository now contains a gated executor that can materialize an ADOPTED mutable evolution plan into one atomic Git commit and open a normal PR against `main`.

Execution requires:

- `AUTOMATE_SELF_EVOLUTION_ENABLED=1`;
- an explicit `AUTOMATE_GITHUB_TOKEN`;
- an exact plan base revision equal to the current remote `main`;
- all update targets to match their expected blob SHA;
- no governance/authority/security path changes.

The executor never merges the PR and never marks the result certified. Normal CI, Security Audit, reconciliation, exact-head verification, and capability-authority bookkeeping remain the final boundary.

This is the machine's first safe path from "I think the system should change" to "I have submitted a reviewable change to the system." It is not yet autonomous constitutional amendment.
