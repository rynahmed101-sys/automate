# Linear Algebra Inner Products and Orthogonality

Third bounded Phase 1A Linear Algebra capability batch for Automate.

Supported rules:

- `vector_inner_product`
- `vector_norm`
- `vector_orthogonal`
- `vector_projection`
- `vector_gram_schmidt`

## Semantics

`vector_inner_product` computes the exact vector inner product. The default is the Hermitian convention, so the first vector is conjugated for complex entries. Set `parameters.hermitian` to `false` only when the bilinear dot product is explicitly intended.

`vector_norm` computes the Euclidean 2-norm. Symbolic results remain exact.

`vector_orthogonal` verifies an indicator claim: output `1` means the Hermitian inner product is exactly zero; output `0` means it is provably non-zero. If symbolic assumptions are insufficient to decide the claim, Automate returns `UNVERIFIED`.

`vector_projection` computes the orthogonal projection of the first vector onto the second. The target vector must be non-zero. If symbolic assumptions do not establish target non-zeroness, verification fails closed as `UNVERIFIED`.

`vector_gram_schmidt` accepts a sequence of equal-dimensional vectors and one output vector for each input. The default produces an orthogonal sequence. Set `parameters.orthonormal` to `true` for an orthonormal sequence. Zero residual vectors and linearly dependent inputs are rejected. Symbolic independence or normalization conditions that cannot be established are returned as `UNVERIFIED`.

Numeric inputs receive an independent NumPy cross-check. This evidence checks the candidate result using NumPy operations and does not constitute a formal proof.

AI agents discover these rules through `automate capabilities --json` and submit them through `automate.proposal.v1` with `target_checker: linear_algebra`.

Named acceptance campaign: `tests/test_linear_algebra_inner_products_acceptance.py`.
