# Finite Uniform Line-Charge Potential

Bounded Phase 2B electrostatics extension.

Automate verifies the exact potential V(r) = k lambda integral_a^b ds / |r - r(s)| for a uniformly charged finite line segment aligned to one explicit Cartesian axis.

The contract requires scalar linear charge density, explicit observation coordinates, an explicit x/y/z source axis, explicit scalar source bounds with a provably positive interval, and an observation point provably off the source segment.

All caller-supplied scalar parameters are parsed through Automate's restricted mathematical parser. This capability does not use unrestricted eval() or SymPy sympify() for source bounds.

This batch is deliberately bounded. It does not claim arbitrary curves, surfaces, automatic distribution discovery, electric-field integration, or Gauss-law verification.
