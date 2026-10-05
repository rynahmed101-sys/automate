# Conductors and Capacitors

This bounded Phase 2B capability family verifies explicit ideal electrostatic conductor and capacitor relations.

## Ideal Cartesian conductor boundary

Rule: `conductor_boundary_field`.

The checker accepts a 3D electric-field vector and an explicit axis-aligned conductor surface normal. It computes the tangential projection

`E_t = E - (E dot n_hat) n_hat`

and requires the reported tangential field to match that projection and to vanish. This represents the ideal-conductor/equipotential boundary condition.

The model is intentionally limited to explicit Cartesian, axis-aligned normals. It does not infer arbitrary curved conductor geometry.

## Ideal parallel-plate field

Rule: `parallel_plate_field`.

For the explicit ideal parallel-plate model,

`E = (sigma / epsilon) n_hat`.

The plate normal and Cartesian coordinate contract are explicit. The model represents the region where the ideal parallel-plate approximation is applicable and does not claim to resolve finite-edge fringing.

## Parallel-plate capacitance

Rule: `parallel_plate_capacitance`.

For explicit parallel rectangular plates with positive area and separation, and with fringing explicitly declared neglected,

`C = epsilon A / d`.

The checker requires the geometry and the negligible-fringing assumption rather than silently treating the finite-plate formula as exact.

## Stored electrostatic energy

Rule: `capacitor_energy`.

For an explicit electrostatic capacitor,

`U = 1/2 C V^2`.

## Verification boundary

All caller-supplied mathematical expressions are parsed through Automate's restricted mathematical parser. Unsafe expressions, invalid geometry, missing model assumptions, incorrect relations, and incompatible boundary conditions fail closed.

The capability is not complete until its acceptance/adversarial tests pass and the merged main head receives authoritative Exact-head CI and Security Audit verification.
