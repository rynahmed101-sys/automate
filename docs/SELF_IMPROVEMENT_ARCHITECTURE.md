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

## 7. What is deliberately not here yet

This foundation does **not** claim that Automate already learns automatically from every execution. The remaining work is wiring experience emission into action cycles, ingesting Mirror/worker evidence, generating richer lessons, running regression suites automatically, and connecting adopted lessons to future worker strategy selection.

Those stages must be built incrementally and tested like any other capability.
