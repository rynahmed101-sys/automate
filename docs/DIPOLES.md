# Bounded Electric Dipoles

This bounded Phase 2B capability family verifies the potential and electric field of an ideal point electric dipole in explicit Cartesian coordinates.

## Point-dipole potential

Rule: `dipole_potential`.

For a point dipole with moment vector `p` at the Cartesian origin and nonzero displacement vector `r`,

`V = k (p dot r) / |r|^3`.

The checker requires the point-dipole model, an explicit origin source position, and Cartesian coordinates. The sign and orientation are carried by the supplied vector components, so positive, negative, axial, and equatorial configurations are independently verifiable.

## Point-dipole electric field

Rule: `dipole_field`.

For the same bounded model,

`E = k [3 (p dot r) r / |r|^5 - p / |r|^3]`.

The field is singular at the dipole location, so zero displacement is rejected rather than treated as a numerical or symbolic special case.

## Verification boundary

This milestone does not infer arbitrary source locations, curvilinear coordinate systems, finite dipole geometry, near-field regularization, or dielectric boundary effects. Those require separate mathematical contracts.

All caller-supplied mathematical expressions continue through Automate's restricted parser. Unsafe expressions, wrong output types, singular geometry, missing model assumptions, and incorrect relations fail closed.

The milestone is not considered certified until acceptance tests, authoritative Exact-head verification, and Security Audit all pass on the relevant merged `main` HEAD.
