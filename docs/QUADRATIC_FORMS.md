# Quadratic Forms

## Scope

Automate's quadratic_form rule verifies the general finite-dimensional real transpose form

q(x) = x^T A x

for a compatible vector x and square matrix A.

The capability is dimension-generic within the existing linear-algebra IR limits. It is not a special-case implementation for a particular polynomial or dimension.

## Semantics

- The first input is a Vector x.
- The second input is a square Matrix A.
- The output is a scalar claim for q(x).
- The matrix does not have to be symmetric.
- Positive-definite, positive-semidefinite, negative-definite, or any other definiteness property is not assumed or tested by this rule.
- Complex-valued forms are currently outside the rule's semantic boundary. The rule therefore fails closed as UNVERIFIED when explicit complex-valued entries are detected rather than silently changing x^T into a conjugate transpose.

SymPy's matrix machinery independently represents transpose and matrix products, while NumPy provides independent matrix multiplication operations used for the numerical evidence route. These libraries are backends/cross-checks; Automate's rule semantics remain defined here.

## Symmetric-part relationship

Every square matrix has

A = (A + A^T)/2 + (A - A^T)/2.

For a real vector x,

x^T A x = x^T ((A + A^T)/2) x

because the antisymmetric contribution

x^T ((A - A^T)/2) x

is exactly zero.

The implementation records this relationship as verification evidence. It does not replace the supplied matrix by its symmetric part for the primary calculation, and it does not require the supplied matrix itself to be symmetric.

## Verification levels

A successful symbolic claim receives SYMBOLIC_CHECKED evidence after exact symbolic equality is established.

For numeric inputs, the result also receives an independent NumPy cross-check using a separate numerical route:

x^T A x

computed with NumPy array operations. Agreement is recorded as independent numerical evidence, not as a formal proof.

If symbolic equality cannot be established, inputs are incompatible, or the domain convention is unsupported, verification fails closed as FAILED or UNVERIFIED according to the existing backend semantics.

## Boundaries

The existing linear-algebra parser currently rejects empty vectors and bounds represented vector/matrix dimensions. Those parser boundaries are inherited rather than quadratic-form-specific restrictions.

The later positive-definite capability should build on this rule but must remain a separate capability: evaluating a quadratic form is not equivalent to establishing definiteness.
