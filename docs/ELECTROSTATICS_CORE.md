# Electrostatics Core

First bounded Phase 2B electromagnetism batch.

Implemented:
- `coulomb_force`
- `point_charge_field`
- `point_charge_potential`

The implementation uses an explicit Coulomb constant `k` (or an equivalent unit-system constant supplied through parameters). Positions/displacements are Cartesian vectors. Coincident source/observation positions fail closed because the point-charge expressions are singular there.

This batch intentionally does not infer charge distributions, material media, boundary conditions, or Gaussian surfaces. Continuous charge distributions and Gauss-law verification belong to later bounded batches.
