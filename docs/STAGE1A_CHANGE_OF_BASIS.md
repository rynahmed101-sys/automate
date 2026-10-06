# Isolated Stage 1A Change-of-Basis Semantics

For an ordered basis represented by a square matrix B whose columns are basis
vectors, and a reference-coordinate vector x, the coordinate vector c is
defined by B c = x. The implementation computes c through B^{-1}x only after
establishing that B is nonsingular, then independently verifies B c = x.

## Evidence states
- SYMBOLIC_CHECKED: basis independence and reconstruction are established exactly.
- FAILED: malformed input, incompatible dimensions, or definite singularity.
- UNVERIFIED: symbolic assumptions are insufficient to establish independence or reconstruction.
- Numeric inputs additionally receive an independent NumPy solve cross-check.

## Boundary
This isolated API handles full-dimensional square bases only. It does not
implement rectangular frames, least-squares coordinates, pseudoinverse
coordinates, affine coordinates, or conversion between two non-reference
bases. It deliberately does not modify central registry, schema, dispatch, or
ledger surfaces; the primary integration pass owns those contracts.
