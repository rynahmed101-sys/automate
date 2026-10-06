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

### Completed Stage 2E scope
The reusable layer now covers 1-D harmonic waves, compatible superposition, a normalized interference observable, equal-amplitude standing waves, exact harmonic wave-equation residual checking, sampled dispersion relations with phase/group velocity evidence, Snell refraction, normal and oblique Fresnel reflectance (including explicit total-internal-reflection classification), Jones polarization with normalized Stokes parameters, and normalized Fraunhofer single-slit diffraction.

Every bounded numerical observable reports explicit evidence status. Unsupported broader semantics remain fail-closed rather than inferred.

### Deliberate boundaries
This does not claim a general vector electromagnetic-wave solver, absorbing/anisotropic media, multilayer transfer matrices, polarization-element composition, full Fresnel transmission phase, near-field/Fresnel diffraction, multi-slit diffraction, or general PDE wave-equation solution families.
