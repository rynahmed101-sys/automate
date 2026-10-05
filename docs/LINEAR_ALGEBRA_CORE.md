# Linear Algebra Core

Phase 1A first bounded capability batch for Automate.

Supported operations: vector addition, subtraction, scalar multiplication, dot products; matrix multiplication, transpose, determinant, trace, inverse, rank, reduced row-echelon form, and unique square-system solving Ax=b.

Canonical values are written as Vector([1, 2, 3]) and Matrix([[1, 2], [3, 4]]). Matrix rows must be rectangular and container dimensions are bounded.

Symbolic verification uses SymPy exact matrix operations. Numeric inputs receive a separate NumPy cross-check recorded as DIFFERENT_ENGINE evidence. This cross-check is computational evidence, not formal proof.

Matrix multiplication requires A.cols == B.rows. Determinant, trace, and inverse require square matrices. Vector binary operations require equal lengths. The initial Ax=b solver accepts only unique square systems and rejects singular/non-unique systems.

Gaussian-elimination evidence records pivots and reduced row-echelon form. All successful checks record expected and actual values, shapes, backend versions, and cross-check metadata.

AI agents should discover these capabilities with automate capabilities --json, retrieve context with automate context, and submit automate.proposal.v1 using target_checker linear_algebra. AI output remains untrusted until the checker returns SYMBOLIC_CHECKED.

Named acceptance campaign: tests/test_linear_algebra_acceptance.py.


## Eigenstructure batch

The next bounded Phase 1A slice adds eigenvalues, explicit eigenvector verification, characteristic polynomials, and diagonalization.

For eigenvalues, the candidate is a Vector containing the algebraic spectrum including multiplicity. Candidate order is not semantically significant.

For an eigenvector, the edge must provide an explicit scalar parameter `eigenvalue`, and the checker verifies the non-zero vector residual `A*v - eigenvalue*v`.

Characteristic-polynomial verification accepts a simple symbolic variable parameter such as `lam` and checks the exact polynomial returned by SymPy's `charpoly`.

Diagonalization accepts two output matrices in order `P`, `D` and verifies that P is invertible, D is diagonal, A = P*D*P^-1, and every column of P is an eigenvector associated with the corresponding diagonal entry.

Numeric eigenvalue/eigenvector/diagonalization results receive NumPy cross-checks where inputs permit. These are recorded as DIFFERENT_ENGINE evidence, not proof.
