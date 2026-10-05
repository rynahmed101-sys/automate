# Quadratic Forms

Automate's Stage 1A quadratic-form capability verifies explicit evaluations of

- real domain: q(x) = x^T A x
- complex domain: q(x) = x^H A x

The rule is `quadratic_form_evaluate`. It accepts a square matrix `A`, a vector `x`, and a scalar candidate result.

## Semantics

The capability deliberately separates **evaluation** from **matrix properties**.

An arbitrary square real matrix can be evaluated directly as x^T A x. It is not silently replaced by its symmetric part. Likewise, an arbitrary complex square matrix can be evaluated as x^H A x; the result need not be real when A is not Hermitian.

When a downstream claim requires a symmetric/Hermitian quadratic form, the edge can request `parameters={"require_hermitian": true}`. Automate then explicitly verifies A = A^H. A false condition is rejected and an unresolved symbolic condition returns `UNVERIFIED`.

For `domain="real"`, the left factor is the ordinary transpose x^T. For `domain="complex"`, the left factor is the conjugate transpose x^H. The domain is explicit rather than inferred from numerical-looking entries.

Dimensions are strict:

- A must be square n x n.
- x must have length n.
- the output must be scalar.

No arbitrary dimension ceiling is introduced by the quadratic-form rule beyond the existing linear-algebra parser representation limits.

## Verification boundary

For exact symbolic inputs, SymPy simplification establishes the claimed equality when decidable. A symbolic expression that is not algebraically equivalent to the required form is rejected; an additional Hermitian property that cannot be established from symbolic assumptions is returned as `UNVERIFIED`.

For numeric inputs, Automate performs an independent NumPy evaluation. The canonical calculation remains the Automate/SymPy expression; NumPy supplies independent numerical evidence only.

The numerical cross-check uses:

- real: `np.dot(x, A @ x)`
- complex: `np.conjugate(x) @ (A @ x)`

This follows the standard complex inner-product convention in which the left vector is conjugated. NumPy documents `vdot` equivalently as conjugating the first vector. citeturn0search24turn0search27

## Degenerate cases

Zero vectors, zero matrices, and rank-deficient matrices are ordinary valid inputs. Their resulting form may be zero without implying positive definiteness.

Positive definiteness is intentionally not part of this rule. Future positive-definite verification can consume the quadratic-form capability rather than duplicate its evaluation semantics.

## Mathematical references

The real quadratic-form representation q(x)=x^T A x is standard. citeturn0search4 Complex Hermitian forms use conjugation and are associated with Hermitian matrices; a Hermitian quadratic form is real-valued on a vector with itself. citeturn0search5turn0search3
