# Core Vector Calculus Identities

Bounded Phase 2A identity family:

- curl(grad f) = 0
- div(curl F) = 0
- equivalent Cartesian scalar Laplacian definitions

The checker is deliberately limited to explicit Cartesian x,y,z coordinates and symbolic differentiation. It fails closed on wrong dimensionality or missing coordinate contracts. These rules verify identities, not arbitrary smoothness assumptions; the rule metadata records the required second partial derivatives.

Acceptance tests cover valid claims, false claims, malformed coordinate contracts, and rule registration.
