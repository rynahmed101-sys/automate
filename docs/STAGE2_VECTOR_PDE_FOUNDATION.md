# Stage 2A/2B implementation notes

This PR adds bounded, reusable mathematical machinery without changing the authoritative phase ledger.

## Stage 2A

CoordinateVectorCalculusChecker represents an explicit orthogonal coordinate system with coordinates and metric scale factors. Supported systems are Cartesian, cylindrical, and spherical. Gradient, divergence, curl, and scalar Laplacian use orthogonal-coordinate scale-factor formulas; unsupported systems and zero scale factors fail closed.

Vector components are physical/basis components. The backend does not relabel Cartesian expressions as non-Cartesian.

reconstruct_potential extends the existing conservative-field checker with an explicit axis-aligned path construction from a supplied base point. The constructed scalar is differentiated back against the original vector field. If equality cannot be established, verification fails/returns UNKNOWN rather than asserting global path independence. This is a local/reconstructive capability, not a theorem that arbitrary domains are simply connected.

## Stage 2B

PDEChecker provides a reusable residual-verification foundation. An equation is supplied explicitly, independent variables and parameters are declared, and a candidate solution is substituted into the equation. The residual is simplified and must be exactly zero for a symbolic pass.

Bounded named rules currently cover heat, wave, Laplace, and Poisson residual forms, but the equation remains explicit rather than pattern-only.

Initial and boundary conditions, separation of variables, Fourier/Laplace transforms, convolution, and Green functions are intentionally not claimed by this PR. They require additional representations and verification contracts.

## Evidence boundary

These capabilities are implementation/review work only. They are not certified and the roadmap ledger is intentionally unchanged.