# Automate Scientific Calculator Ledger

Version: 2.0
Established: 2026-10-09
Authority: sole operational ledger for Automate.

## 1. Purpose

Automate is a general-purpose, AI-compatible mathematics and physics calculation engine.

Its job is simple:

**AI interprets the problem. Automate does the mathematics/physics operations. AI interprets the result.**

Automate is a calculator and scientific computation workbench, not a scientific authority, teacher, gatekeeper, or autonomous software-development system.

It must not try to decide whether a mathematical or physical idea is philosophically legitimate, fashionable, established, novel, or acceptable. If the operation can be represented and computed, Automate should attempt it.

## 2. What Automate should provide

Automate should make it easy for an AI to perform:

- arithmetic
- algebra
- symbolic manipulation
- equations and systems
- calculus
- multivariable calculus
- linear algebra
- numerical mathematics
- differential equations
- vectors and matrices
- tensors and geometry
- mechanics
- electromagnetism
- thermodynamics
- statistical physics
- quantum mechanics
- relativity
- other mathematical/physical operations that can be represented by its available backends

Use mature engines rather than rebuilding mathematics unnecessarily:

- SymPy
- NumPy
- SciPy
- EinsteinPy
- Lean/Mathlib where useful
- other suitable scientific libraries as capabilities expand

## 3. The boundary

The AI is responsible for interpretation.

Automate is responsible for calculation.

Example:

AI:
"Find the Jacobian of these three expressions with respect to x, y and z."

Automate:
"Here is the Jacobian."

AI:
"Interpret that Jacobian for the physical model."

Automate does not need to become the physicist.

Likewise, if an AI proposes an unusual or nonstandard equation, Automate should not reject it merely because it is unusual. It should calculate whatever mathematical operations are requested and report ordinary computational failures honestly.

## 4. No scientific bureaucracy

Remove unnecessary machinery whose only purpose is to make a calculator behave like a scientific approval board.

Do not require:

- authorization for ordinary mathematical operations
- a concept to be "legitimate" before calculation
- provenance paperwork for every answer
- formal proof before returning a calculation
- independent cross-checks for every basic operation
- elaborate certification states for ordinary calculator functions
- AI-facing philosophical restrictions on mathematical exploration
- rejection merely because a physical model is unconventional

Evidence, verification, assumptions, domains, and provenance may still be returned when they are useful or requested. They are features, not bureaucratic gates.

## 5. Failure rule

Fail only for an actual computational or input problem, such as:

- malformed input
- unsupported operation
- undefined mathematical operation
- incompatible dimensions/types where the backend cannot resolve them
- numerical failure
- backend failure
- resource limits

Return the useful result whenever computation succeeds.

Do not turn "I cannot prove this is physically true" into "I cannot calculate it."

A calculation and a scientific claim are different things.

## 6. Calculator architecture

Preferred flow:

**AI interpretation**
→ **structured calculation request**
→ **Automate**
→ **backend calculation**
→ **result**
→ **optional checks/details**
→ **AI interpretation**

The structured interface should be stable and simple.

Automate should expose reusable operations rather than enormous domain-specific workflows whenever the underlying mathematics can be shared.

## 7. Verification philosophy

Verification is useful, but proportional.

For simple deterministic operations:

**calculate → return result**

For operations where an inexpensive check materially improves reliability:

**calculate → check → return result**

For expensive, numerical, approximate, or scientifically consequential operations:

**calculate → optional/appropriate diagnostics → return result**

Do not force heavyweight verification onto every calculator operation.

A calculator does not need an authorization letter after calculating 2 + 2.

## 8. Scientific openness

Automate must be capable of operating on:

- established mathematics
- established physics
- hypothetical mathematics
- unconventional equations
- exploratory models
- incomplete models
- user-defined mathematical structures

The engine should distinguish computational failure from scientific interpretation.

For example:

If an equation is mathematically inconsistent, report the mathematical inconsistency.

If it is mathematically computable but physically unvalidated, calculate it anyway.

The AI can decide what the result means.

## 9. Capability development

Development is now capability-first rather than bureaucracy-first.

For each useful mathematical/physical operation:

1. Check whether an existing backend already performs it.
2. Expose it through Automate's interface.
3. Add the minimum semantic handling needed to pass the request correctly.
4. Add a small focused test.
5. Add failure tests where failure is realistically possible.
6. Run the relevant existing test suite.
7. Review the diff.
8. Merge when the implementation is sound.

Do not create layers merely because a previous AI considered them architecturally impressive.

The question is:

**Can an AI ask Automate to perform useful mathematics or physics and reliably get the result?**

If yes, the capability is doing its job.

## 10. Development priority

Build broad useful mathematical capability first, then expand into physics.

Priority families:

### Mathematics
- arithmetic
- algebra
- simplification
- equations
- polynomials
- functions
- limits
- derivatives
- integrals
- series
- multivariable calculus
- optimization
- linear algebra
- numerical methods
- ODEs
- PDEs
- transforms
- probability/statistics

### Physics
- units/dimensions
- vectors and fields
- mechanics
- waves
- electromagnetism
- thermodynamics
- statistical physics
- relativity
- quantum mechanics
- tensors/geometry
- broader mathematical physics

The order is flexible when an existing backend makes a capability cheap and useful.

Do not block useful physics work simply because an arbitrary mathematics stage is incomplete.

## 11. Current implementation and immediate work

The direct calculator interface has advanced through PRs #214-#221. Current
main includes the discoverable Python/CLI API and structured request route;
native SymPy inputs; typed result data; nth derivatives, definite integrals,
directional limits, configurable series, multi-equation systems, ODE/PDE
solving, transforms, multivariable Jacobians/Hessians, and stationary-point
candidates; plus Pint conversion, descriptive statistics, and allowlisted
SciPy distribution evaluation.

PR #221 was merged as
`347a5290f65498eafbfccc912f7d4a19ff1f3291`. On that exact main SHA, Automate
CI run `37971635225` and Security Audit run `37971635286` both completed
successfully. These establish repository test/security workflow status for
that commit; they do not establish formal proof or independent verification
of every result.

The current practical queue is:

1. Review and integrate the current calculator contract increment. It wires
   the remaining manifest arguments into `automate calculate`, makes JSON
   calculation errors return a failing process status, and adds direct total
   differential and Cartesian divergence, curl, and Laplacian operations.
   These changes are on the working branch, not in the exact-main evidence
   recorded above.
2. Expose useful existing lower-level mathematical-physics operations through
   compact calculator requests where doing so preserves their current model
   and domain contracts. Mechanics, electromagnetism, tensor/geometry, and
   vector-calculus graph verifiers remain distinct from ordinary calculator
   expressions unless an operation is deliberately added.
3. Address bounded constrained optimization and explicit domain/assumption
   semantics only with contracts that distinguish candidate results from
   classification or proof.
4. Reconcile remaining issue tracking without equating CI success with formal
   proof or certification.
5. If Automate is used as a concurrent service, add an explicit aggregate
   parser-worker policy. Existing AST, output, CPU, wall-clock, and per-worker
   address-space limits do not cap the number of workers across concurrent
   requests.

The requirements recorded in issue #115 (improper integrals) and issue #141
(Taylor/Maclaurin series) are implemented and covered by focused tests. Issue
#141 is closed as completed. Issue #115 remains open pending review of the
improper-integral safeguards on this working branch. This branch rejects
reversed infinite bounds and out-of-interval or unresolved interior split
points rather than assigning a convergence classification.

Keep old operation behavior compatible unless the change is explicitly
additive. Every exposed operation must be callable, described truthfully in the
manifest, and covered by focused tests.

## 12. Existing documentation

This ledger replaces the former phase-ledger/roadmap split.

Retired operational documents:

- docs/PROJECT_PHASE_LEDGER.md
- docs/MATH_PHYSICS_ROADMAP.md

docs/CAPABILITY_INVENTORY.json is an inventory/evidence index only.

docs/correct-10-stage-machinery-map-20261008 is historical reference only.

No competing roadmap should be created.

## 13. Operating rule

Future agents must:

1. Read this ledger.
2. Inspect the actual current repository.
3. Identify useful missing calculator/scientific capabilities.
4. Prefer existing scientific backends.
5. Implement the smallest useful interface.
6. Test it.
7. Review the complete diff.
8. Merge sound work.
9. Move to the next useful capability.

Do not stop development to manufacture additional governance unless the repository has a real engineering problem requiring it.

Do not turn every calculator operation into a research certification project.

## 14. Success criterion

Automate succeeds when an AI can hand it mathematical or physical data, ask for an operation, receive a correct computational result, and continue reasoning without unnecessary friction.

The AI remains the interpreter.

Automate remains the calculator.

That is the product.


## Recovered calculator capability increment (merged)

PR #221 integrated Pint-based unit conversion, descriptive statistics for
finite real numeric sequences and vectors, allowlisted SciPy distribution
evaluation, supported symbolic PDE solving, safer stationary-point handling,
mapping and quantity serialization, and the corresponding CLI/manifest
entries. Its merge commit is
`347a5290f65498eafbfccc912f7d4a19ff1f3291`.

On that exact main SHA, Automate CI run `37971635225` and Security Audit run
`37971635286` both completed successfully. This establishes the repository
workflow results for that commit, not formal proof or independent verification
of every mathematical result.
