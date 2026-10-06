# Moore-Penrose Pseudoinverse and Linear Least Squares

Automate's Stage 1A linear-algebra verifier treats the Moore-Penrose pseudoinverse and least-squares solutions as explicit verification capabilities rather than opaque numerical calculations.

## Moore-Penrose pseudoinverse

For a matrix A and candidate A+, the verifier checks all four Moore-Penrose conditions:

- A A+ A = A
- A+ A A+ = A+
- (A A+)^H = A A+
- (A+ A)^H = A+ A

The candidate must have shape n x m for an m x n input. Empty matrices are rejected. Symbolic conditions that cannot be decided exactly return UNVERIFIED rather than being guessed.

Numeric inputs also receive an independent NumPy pseudoinverse cross-check. NumPy is evidence, not the semantic authority.

## Linear least squares

For A x approximately equal to b, the verifier checks the normal equations

A^H(Ax-b) = 0

and verifies minimum-norm membership by requiring the candidate to be orthogonal to the null space of A. This distinguishes the minimum-norm least-squares solution from other solutions that can satisfy the normal equations when A is rank deficient.

Numeric inputs receive an independent NumPy pinv(A) @ b cross-check.

## Boundaries

The capability does not infer parameter assumptions or silently accept unresolved symbolic identities. Shape errors, malformed claims, incorrect candidates, and unresolved symbolic conditions fail closed.

The implementation reuses the existing linear-algebra IR, parser, checker, rule registry, machine-agent schema, and evidence model.
