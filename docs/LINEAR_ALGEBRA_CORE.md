# Linear Algebra Core

Phase 1A first bounded capability batch for Automate.

Supported operations: vector addition, subtraction, scalar multiplication, dot products; matrix multiplication, transpose, determinant, trace, inverse, rank, reduced row-echelon form, and unique square-system solving Ax=b.

Canonical values are written as Vector([1, 2, 3]) and Matrix([[1, 2], [3, 4]]). Matrix rows must be rectangular and container dimensions are bounded.

Symbolic verification uses SymPy exact matrix operations. Numeric inputs receive a separate NumPy cross-check recorded as DIFFERENT_ENGINE evidence. This cross-check is computational evidence, not formal proof.

Matrix multiplication requires A.cols == B.rows. Determinant, trace, and inverse require square matrices. Vector binary operations require equal lengths. The initial Ax=b solver accepts only unique square systems and rejects singular/non-unique systems.

Gaussian-elimination evidence records pivots and reduced row-echelon form. All successful checks record expected and actual values, shapes, backend versions, and cross-check metadata.

AI agents should discover these capabilities with automate capabilities --json, retrieve context with automate context, and submit automate.proposal.v1 using target_checker linear_algebra. AI output remains untrusted until the checker returns SYMBOLIC_CHECKED.

Named acceptance campaign: tests/test_linear_algebra_acceptance.py.


## Linear transformations and matrix representations

A finite-dimensional linear transformation is represented by a matrix A and applied to an input vector x as y = A x. Rectangular matrices are supported, so domain and codomain dimensions may differ. Verification rejects incompatible dimensions and compares the candidate output against exact symbolic matrix action; numeric inputs also receive an independent NumPy matrix-vector cross-check.

The matrix representation rule reconstructs a unique map from an explicit invertible domain basis B and the corresponding image columns C by verifying M B = C, equivalently M = C B^-1. Singular bases are rejected, while symbolic parameterized bases whose invertibility cannot be established are returned as UNVERIFIED rather than assumed valid.

These rules establish reusable transformation semantics without depending on the pending change-of-basis capability.


## Symmetric and Hermitian matrices

Automate verifies square matrices for the symmetric condition A = A^T and the Hermitian condition A = A†. Numeric inputs receive independent NumPy checks. Symbolic Hermitian claims that depend on unresolved conjugation assumptions fail closed as UNVERIFIED rather than treating an unconstrained symbol as real.


## Positive-definite matrices

Positive definiteness is verified only for square matrices whose symmetric/Hermitian condition can be established. Exact symbolic cases use Sylvester's criterion through the leading principal minors; unresolved positivity or conjugation assumptions fail closed as UNVERIFIED. Numeric matrices also receive an independent NumPy Hermitian-eigenvalue check with a scale-aware tolerance.
