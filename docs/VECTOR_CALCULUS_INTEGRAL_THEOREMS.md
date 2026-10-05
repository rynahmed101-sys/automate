# Vector Calculus Integral Theorems

Third bounded Phase 2A batch.

Implemented theorem verification is intentionally limited to explicit Cartesian domains:

- `green_theorem`: counterclockwise circulation around a rectangle equals the area integral of planar curl.
- `divergence_theorem`: outward flux through a rectangular box equals the volume integral of divergence.
- `stokes_theorem`: counterclockwise boundary circulation, viewed from the positive normal, equals the curl flux through a planar rectangular surface.

Each theorem requires an explicit orientation contract. Missing or incompatible orientation/domain metadata fails closed.

The checker constructs the boundary-side integral and derivative-side integral separately, then verifies their symbolic difference is zero. This batch does not claim arbitrary manifolds, curved boundaries, topology-aware domains, or automatic regularity proofs. Those require stronger geometry and assumption semantics and remain outside this bounded implementation.

Acceptance campaign: `tests/test_vector_calculus_integral_theorems.py`.
