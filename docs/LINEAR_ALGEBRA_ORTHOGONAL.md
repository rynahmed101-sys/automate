# Orthogonal Matrix Semantics

Stage 1A treats orthogonal matrices as an explicit real-matrix capability.

For a square matrix Q, the defining condition is Q^T Q = I. Matrices with complex entries are not silently treated as orthogonal. Symbolic uncertainty about entry reality or the product identity returns UNVERIFIED.

NumPy is used only for an independent numerical cross-check. It cannot convert an unresolved symbolic claim into a verified one.

The capability is not certified until the merged-main commit carrying it passes the authoritative Exact-head and Security Audit gates.
