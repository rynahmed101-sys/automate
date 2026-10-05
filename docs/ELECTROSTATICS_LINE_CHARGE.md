# Finite Uniform Line-Charge Potential

Bounded Phase 2B electrostatics extension.

The checker computes the potential
V = k λ ∫ ds / |r - r'|
for a uniformly charged finite line segment aligned with one explicit Cartesian axis.

The contract requires:
- explicit x/y/z coordinates;
- an explicit source axis;
- explicit source bounds;
- a non-zero source interval;
- an observation point that does not coincide with a source endpoint.

This is deliberately not a generic charge-distribution engine yet. Continuous distributions, arbitrary curves/surfaces, electric-field integration, and Gauss-law verification remain separate batches.
