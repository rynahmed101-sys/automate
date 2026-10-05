# Linear Algebra Subspaces, Span, and Independence

Phase 1A subspace capability family for Automate.

The family verifies subspace claims using exact SymPy linear algebra and an independent NumPy rank cross-check for numeric inputs.

## Representations

All basis vectors are represented as columns of a Matrix.

- matrix_null_space: candidate columns must form a basis of ker(A). Automate checks A*N = 0 and that the candidate rank equals the exact nullity.
- matrix_row_space: candidate columns are basis vectors for the row space of A. Automate compares the exact rank of A.T, the candidate, and their combined span.
- matrix_column_space: candidate columns must form a basis of col(A).
- vector_span_membership: the first input is a generator matrix whose columns define a span; the second input is tested for membership. Output 1 means inside and 0 means outside.
- vector_linear_independence: the columns of the generator matrix are tested for independence. Output 1 means independent and 0 means dependent.
- vector_basis_of_span: verifies that the candidate basis columns are independent and span exactly the same subspace as the generator columns.

## Domain restrictions

Subspace rank semantics are fail-closed for symbolic parameter domains. If the supplied matrices contain free symbolic parameters, Automate returns UNVERIFIED rather than silently assuming generic non-zero values.

Zero-dimensional subspaces are explicitly representable with zero-column matrices such as Matrix([[], []]).

Unsafe constructors, malformed matrices, ragged rows, dimension mismatches, and incorrect indicators are rejected.

## Evidence

Numeric claims receive an independent numpy.linalg.matrix_rank cross-check. The NumPy result is evidence, not a formal proof.

Named acceptance campaign: tests/test_linear_algebra_subspaces_acceptance.py.