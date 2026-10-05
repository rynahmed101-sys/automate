# Stage 2E — Waves and Optics Foundation

This batch establishes reusable 1-D harmonic-wave and bounded basic-optics primitives.

## Implemented

- Harmonic traveling-wave representation with amplitude, angular frequency, wavenumber, phase, and explicit propagation direction.
- Compatible same-direction harmonic superposition reduced to canonical amplitude/phase form.
- Standing-wave construction from equal counter-propagating components.
- Phase velocity from explicit dispersion data.
- Normal-incidence Fresnel reflectance and Snell refraction with total-internal-reflection failure.
- Complex two-component transverse polarization (Jones-state normalization).
- Basic Fraunhofer single-slit diffraction normalized intensity.

## Evidence boundary

These are explicit mathematical models, not claims that a physical configuration exists. Reflection/refraction requires positive refractive indices and a supplied incidence angle; total internal reflection has no real refracted angle. Group velocity is never invented without an explicit dispersion relation.

Basic diffraction is deliberately limited to the single-slit Fraunhofer intensity model. Full wave-optics propagation, near-field diffraction, apertures, boundary conditions, multilayer optics, and polarization propagation are not claimed.

## Incomplete

- General vector/spacetime wave fields.
- Dispersion-curve construction and group velocity from omega(k).
- Fresnel amplitude coefficients for oblique incidence and polarization.
- Boundary/interface field matching.
- Multi-element polarization optics.
- Double/multi-slit and Fresnel diffraction.
- PDE-level wave-equation solution families.
