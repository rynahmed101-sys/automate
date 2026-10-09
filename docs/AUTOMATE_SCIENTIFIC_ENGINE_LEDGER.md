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

## 11. Current immediate work

The calculator surface has been integrated into `main` through PRs #214, #215, and #216:

- a unified calculator API and CLI operation surface
- native SymPy object handling and aligned package/CLI version metadata
- a discoverable machine-readable calculator manifest
- structured Python requests and a JSON CLI request command
- typed JSON results while retaining the readable result field

The next capability increment is broader reusable calculus, not more governance:

- nth derivatives
- definite integrals with explicit lower and upper bounds
- directional limits
- series expansion around a configurable point
- equation systems with more than two equations

Keep old operation behavior compatible unless the change is explicitly additive. Every exposed operation must be callable, described truthfully in the manifest, and covered by focused tests. Verify the exact commit on `main` before describing it as certified.

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
