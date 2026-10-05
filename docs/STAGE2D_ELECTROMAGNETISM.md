# Stage 2D Electromagnetism Foundation

This branch establishes reusable representations for electromagnetic fields,
sources, potentials, and constitutive assumptions. It does not claim full
Maxwell or Stage 2D completion.

## Existing repository capability

The current repository already contains a substantial electrostatics backend:
point-charge fields/potentials, Coulomb force, continuous charge kernels,
finite line-charge potential, Gauss-law box verification, dipole field/potential,
conductor boundary field, parallel-plate field/capacitance, and capacitor energy.
These capabilities are preserved rather than duplicated.

## New reusable layer

ElectromagneticSystem composes electric/magnetic fields, charge/current sources,
optional scalar/vector potentials and gauge metadata, constitutive relations,
and explicit assumptions and independent variables.

## Boundary

Not claimed here: full Maxwell-equation verification, gauge-transformation verification,
electromagnetic wave derivation, Lorentz-force dynamics, Poynting theorem,
boundary/interface conditions, radiation, or relativistic field transformations.

Unsupported or ambiguous cases must remain unresolved rather than being inferred.