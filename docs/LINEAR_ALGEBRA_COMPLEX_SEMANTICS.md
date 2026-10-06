# Linear Algebra Complex Semantics

Stage 1A exposes explicit adjoint and unitary semantics needed by later spectral and quantum reasoning.

`matrix_conjugate_transpose` verifies the exact conjugate-transpose of a real or complex matrix.

`matrix_unitary` verifies the square-matrix identity A^H A = I. Symbolically undecidable conditions return UNVERIFIED rather than being guessed.

SymPy provides canonical symbolic semantics. NumPy is independent numerical evidence only.

The capability is not considered certified until its merged main commit passes authoritative Exact-head and Security Audit checks.
