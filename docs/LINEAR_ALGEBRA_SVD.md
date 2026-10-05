# Singular Value Decomposition

Automate's Stage 1A SVD capability verifies an explicit reduced/thin singular value decomposition for general real and complex matrices.

For A with shape m x n, k = min(m,n), the canonical representation is A = U Sigma V* with U of shape m x k, Sigma of shape k x k, and V* of shape k x n. Sigma is diagonal with real, non-negative, non-increasing singular values. U has orthonormal columns and V has orthonormal columns, expressed through U^H U = I and V* V^H = I. Reconstruction must equal A.

The rule id is `matrix_svd`. It verifies explicit factors rather than claiming a general symbolic SVD constructor.

## Verification semantics

The checker validates dimensions, diagonal Sigma structure, singular-value reality/non-negativity/order, conjugate-transpose orthogonality, and reconstruction. Exact symbolic uncertainty in sign or ordering fails closed as UNVERIFIED.

Numeric inputs additionally receive an independent NumPy SVD cross-check. NumPy is evidence only and does not define Automate's canonical semantics.

Rank-deficient matrices and zero singular values are valid. Complex matrices use conjugate transpose. Singular vectors are not compared individually to an external implementation because sign/phase and repeated-singular-value subspace choices are non-unique.

## Scope boundary

This capability does not construct arbitrary symbolic SVD factors. Full square-unitary completion is outside the canonical reduced/thin representation.
