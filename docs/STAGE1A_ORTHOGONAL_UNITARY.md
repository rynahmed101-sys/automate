# Isolated Stage 1A Orthogonal / Unitary Matrix Semantics

This packet adds a reusable mathematical primitive for matrix transformations:

- orthogonal: real square matrix Q with Q^T Q = Q Q^T = I;
- unitary: complex-capable square matrix U with U^dagger U = U U^dagger = I.

The implementation is intentionally isolated from the central rule registry and agent schema. That keeps the packet integration-friendly while the primary agent reconciles the current Stage 1A contract.

## Evidence semantics

- SYMBOLIC_CHECKED means both defining product identities were established exactly as zero.
- FAILED means a shape, reality condition, or defining identity is definitely violated.
- UNVERIFIED means symbolic assumptions are insufficient to establish the property.
- Numeric inputs receive a separate NumPy product check labeled DIFFERENT_ENGINE. It is supporting evidence, not a proof.

## Domain restrictions

1. Orthogonal matrices are explicitly real. A complex-orthogonal matrix is not silently classified as orthogonal.
2. Unitary matrices may contain real or complex entries.
3. Both properties require square matrices.
4. Symbolic reality or conjugation conditions that cannot be established fail closed as UNVERIFIED.
5. No tolerance is used for the symbolic decision.
6. Numeric tolerance is used only by the independent NumPy cross-check.

## Why this is useful

The primitive is a reusable bridge for change-of-basis, orthonormal-coordinate transformations, complex spectral work, SVD-related reasoning, and later quantum-mechanical unitary operators. It does not implement those higher-level capabilities itself.

## Deliberately not included

- central rule registration;
- agent-schema exposure;
- proposal-dispatch integration;
- ledger edits;
- Exact-head or Security workflow changes;
- rectangular isometries;
- approximate/projected orthogonality;
- determinant-only shortcuts.

The primary integration pass should add the smallest appropriate rule/registry/schema surface after reviewing this packet against current-main contracts.
