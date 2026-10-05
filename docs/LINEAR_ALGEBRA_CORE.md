# Linear Algebra Core

Phase 1A first bounded capability batch for Automate.

Supported operations: vector addition, subtraction, scalar multiplication, dot products; matrix multiplication, transpose, determinant, trace, inverse, rank, reduced row-echelon form, and unique square-system solving Ax=b.

Canonical values are written as Vector([1, 2, 3]) and Matrix([[1, 2], [3, 4]]). Matrix rows must be rectangular and container dimensions are bounded.

Symbolic verification uses SymPy exact matrix operations. Numeric inputs receive a separate NumPy cross-check recorded as DIFFERENT_ENGINE evidence. This cross-check is computational evidence, not formal proof.

Matrix multiplication requires A.cols == B.rows. Determinant, trace, and inverse require square matrices. Vector binary operations require equal lengths. The initial Ax=b solver accepts only unique square systems and rejects singular/non-unique systems.

Gaussian-elimination evidence records pivots and reduced row-echelon form. All successful checks record expected and actual values, shapes, backend versions, and cross-check metadata.

AI agents should discover these capabilities with automate capabilities --json, retrieve context with automate context, and submit automate.proposal.v1 using target_checker linear_algebra. AI output remains untrusted until the checker returns SYMBOLIC_CHECKED.

Named acceptance campaign: tests/test_linear_algebra_acceptance.py.


## Symmetric and Hermitian matrices

Automate verifies square matrices for the symmetric condition A = A^T and the Hermitian condition A = A†. Numeric inputs receive independent NumPy checks. Symbolic Hermitian claims that depend on unresolved conjugation assumptions fail closed as UNVERIFIED rather than treating an unconstrained symbol as real.
