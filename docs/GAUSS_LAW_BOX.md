# Bounded Gauss-Law Verification

Automate verifies Gauss's law for an explicit Cartesian rectangular box:

Φ_E = Q_enclosed / ε₀.

The contract requires a 3D electric field, scalar charge density, explicit x/y/z coordinates, three positive finite bounds, explicit outward orientation, and explicit epsilon0. The checker independently constructs the six outward face-flux integrals and the enclosed volume-charge integral, then requires both the reported flux and the Gauss-law equality to hold exactly.

Caller-supplied bounds and epsilon0 are parsed through Automate's restricted mathematical expression parser. Unsupported or unsafe geometry fails closed.

This capability is intentionally bounded. It does not claim arbitrary closed surfaces, conductors, symmetry inference, or automatic geometry discovery.
