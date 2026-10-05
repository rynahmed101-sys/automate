# Linear Algebra Eigenproblems

Second bounded Phase 1A capability batch for Automate.

Supported rules:

- matrix_characteristic_polynomial
- matrix_eigenvalues
- matrix_eigenvector
- matrix_diagonalize

Characteristic polynomials use the explicit generator supplied in parameters.symbol and follow the convention det(lam*I - A). The default generator is lam. Python's lambda keyword is intentionally not accepted as a scalar-generator identifier.

matrix_eigenvalues returns the complete eigenvalue multiset, including algebraic multiplicity. Candidate ordering does not matter. The checker requires every expected eigenvalue to be representable through Automate's safe scalar boundary. If the symbolic backend cannot complete the spectrum or the result exceeds that boundary, Automate returns UNVERIFIED rather than inventing a result.

matrix_eigenvector verifies the actual eigenvector claim A*v = lambda*v and requires a non-zero vector. Any valid scaling of a correct eigenvector is accepted.

matrix_diagonalize verifies a proposed pair (P, D) by checking D is diagonal, P is invertible, and A = P*D*P^-1. For symbolic P, this batch requires its determinant to be an explicitly non-zero constant because parameter-dependent invertibility needs assumptions that this batch does not yet encode.

For numeric matrices and candidates, NumPy provides an independent numerical cross-check. Eigenvalues are compared as unordered multisets; eigenvectors are checked by residual norm plus an independent eigenvalue check; diagonalizations are checked by reconstruction and independent spectrum agreement. Numeric evidence is not promoted to formal proof.

AI agents should discover the expanded rule family using automate capabilities --json, retrieve context with automate context, and submit automate.proposal.v1 with target_checker: linear_algebra.

Acceptance boundary: tests/test_linear_algebra_eigen_acceptance.py.
