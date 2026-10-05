# Stage 2D Electromagnetism

Stage 2D now has reusable electromagnetic representations plus core field-equation and energy-force verification.

## Implemented

- typed electric/magnetic field, source, potential, and constitutive representations;
- all four Maxwell residuals for homogeneous isotropic SI media;
- Lorentz-force construction from explicit field and velocity components;
- Poynting-theorem residual verification for homogeneous media;
- existing electrostatics machinery remains the source for point-charge, continuous-charge, dipole, conductor, capacitor, and Gauss-law capabilities.

## Explicit assumptions

Maxwell verification assumes Cartesian components, SI units, scalar homogeneous permittivity and permeability, and source terms represented as rho and J. Vector inputs are explicit three-component comma-separated expressions.

## Boundaries

Not claimed: spatially varying/tensor constitutive media, material interfaces, radiation/retarded potentials, relativistic field transformations, general gauge transformations, or closed-form electromagnetic wave solution families.

Unsupported or ambiguous cases remain unresolved rather than inferred.
