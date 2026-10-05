# Limits and Continuity

Automate's Stage 1B limits foundation verifies scalar one-variable limit and pointwise continuity claims without replacing a limit by direct substitution.

## Representation

A limit edge has one scalar expression input and one scalar result output. Required parameters:

- variable: the explicit limit variable, e.g. x.
- point: the target expression, e.g. 0, a, oo, or -oo.
- direction: one of two_sided, left, right, +infinity, or -infinity.
- assumptions (optional): explicit symbol assumptions supported by the existing SafeParser/SymPy representation (real, positive, negative, nonzero, integer).

The result may be an exact scalar expression, oo, -oo, or the explicit marker DNE / DOES_NOT_EXIST / NONEXISTENT.

The implementation never treats f(a) as a limit. For a finite two-sided limit it computes both one-sided limits and requires them to agree. One-sided direction is retained explicitly. Infinite targets are represented as +infinity or -infinity.

## Continuity

A continuity edge uses the same expression/variable/point representation and requires a finite two-sided target. Its output is an explicit indicator:

- 1 — lim(x->a) f(x) = f(a) is established.
- 0 — continuity is not established at the point, including an undefined function value or unequal one-sided limits.

This is intentionally an indicator rather than a disconnected continuity formula: the checker evaluates f(a), establishes the two-sided limit through the limit machinery, and then compares the two exact values.

A removable discontinuity therefore remains a discontinuity for the original function when f(a) is undefined, even if the surrounding limit exists.

## Domain and failure semantics

The scalar calculus foundation uses real one-variable semantics. For finite targets, the checker conservatively consults SymPy real-domain analysis before claiming an approach path. If the representation cannot establish that the required side(s) are in the real domain, the result is UNVERIFIED.

Other fail-closed cases include:

- unresolved symbolic limit computation;
- unresolved symbolic comparison;
- unsupported directions;
- missing variable or target;
- malformed expressions rejected by SafeParser;
- continuity requested at an infinite target.

A numerical sample is never used to upgrade an exact claim. It is recorded only as independent evidence.

## Independent numerical evidence

For numeric expressions, deterministic NumPy sampling probes points approaching the finite target or growing toward an infinite target. The evidence records the sampling engine, points, values, tolerance where applicable, and evidence_only: true.

This route is intentionally independent of SymPy's symbolic limit algorithm. It can corroborate a symbolic result but cannot prove a limit or continuity statement.

## Scope boundaries

The foundation is intentionally scalar and one-variable. It does not claim multivariable limits, epsilon-delta proof construction, uniform continuity, or complex-path limits. Those require additional representations and domain semantics.

## Research basis

SymPy's documented limit API supports explicit right/left direction and infinite targets; Automate explicitly performs both one-sided computations for a two-sided claim so that the semantics are not inherited from a single directed computation. SymPy's assumptions system is used only when assumptions are explicitly supplied.

References:
- https://docs.sympy.org/latest/modules/series/series.html
- https://docs.sympy.org/latest/tutorial/calculus.html
- https://docs.sympy.org/latest/guides/assumptions.html

Roadmap status is intentionally unchanged; implementation and CI are not certification.