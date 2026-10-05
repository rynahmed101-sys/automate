# Phase 2A Vector Calculus

Bounded first Vector Calculus capability family for Automate.

Implemented and exposed through the agent contract:

- `scalar_field`
- `vector_field`
- `gradient`
- `directional_derivative`
- `divergence`
- `curl` in 3D Cartesian coordinates
- `laplacian` for scalar fields
- `conservative_field` / potential equality

The implementation uses exact SymPy differentiation for mathematical verification. Numeric claims also receive deterministic finite-difference evidence through NumPy. That evidence is explicitly labeled as independent numerical evidence, not as a formal proof.

The first batch deliberately does not include line/surface/volume integration or Green/Divergence/Stokes theorem checking. Those are separate capabilities with substantially different boundary-condition and orientation semantics and should be added as later bounded batches.

Coordinate systems are explicit through `parameters.coordinates`; no hidden coordinate convention is assumed when the dimension matters.

AI agents discover these rules through `automate capabilities --json`, receive them in `automate context`, and submit them through the existing proposal/verification path with `target_checker: vector_calculus`.

Acceptance campaign: `tests/test_vector_calculus_phase2a.py`.
