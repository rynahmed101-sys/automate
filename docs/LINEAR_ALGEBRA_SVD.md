# Singular Value Decomposition

Automate's Stage 1A SVD rule is an explicit **verification** capability for the reduced/thin singular value decomposition.

For an arbitrary real or complex matrix A with shape m x n, let k = min(m,n). The canonical representation is:

A = U Sigma V*

with:

- U: m x k, with U* U = I_k;
- Sigma: k x k diagonal, real, non-negative, and ordered sigma_1 >= ... >= sigma_k >= 0;
- V*: k x n, with V* V* = I_k when read as V^H V = I_k;
- reconstruction U Sigma V* = A.

The rule id is `matrix_svd`. A derivation edge supplies one matrix input and three output nodes in order: U, Sigma, V*. This is intentionally the reduced/thin convention rather than the full square-unitary convention. It avoids unnecessary null-space completion while retaining all k singular values, including zeros.

## Verification semantics

The checker validates dimensions before identities. It then verifies:

1. Sigma is diagonal.
2. Every singular value is real and non-negative.
3. Singular values are non-increasing.
4. U^H U = I_k.
5. V^H V = I_k, represented in the edge as V* V^H = I_k.
6. U Sigma V* = A.

For exact symbolic inputs, these conditions are established with SymPy exact simplification. If non-negativity or ordering depends on unresolved symbolic assumptions, the result is **UNVERIFIED**, not guessed.

For fully numeric inputs, Automate additionally performs an independent numerical cross-check using NumPy's SVD implementation. The cross-check compares singular values and independently evaluates reconstruction and orthogonality residuals. NumPy is evidence only; it is not the source of Automate's canonical semantics.

Complex matrices use conjugate transpose throughout. The implementation does not compare individual singular vectors to an external result because vectors are not unique under sign/phase changes (and rotations within repeated-singular-value subspaces).

## Rank deficiency and zero singular values

Rank-deficient matrices are valid. Zero singular values are retained in the k-length Sigma representation. A zero singular value does not require a special rejection; it is part of the ordinary reduced SVD semantics.

## Scope boundary

This capability verifies explicit SVD factors. It does not claim a general symbolic SVD constructor for arbitrary parameterized matrices. That constructor is a separate capability and must remain fail-closed when the exact singular vectors/values cannot be established.

External numerical conventions were cross-checked against NumPy/SciPy documentation. NumPy and SciPy both use k = min(m,n) singular values, descending order, and support reduced/full rectangular SVD representations.
