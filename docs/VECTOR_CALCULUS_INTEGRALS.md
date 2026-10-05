# Vector Calculus Cartesian Integrals

Second bounded Phase 2A batch.

Implemented:

- `line_integral_scalar`
- `line_integral_vector`
- `surface_integral_scalar`
- `surface_flux`
- `volume_integral`

All parameterizations and bounds are explicit. Line and surface integrals require declared Cartesian coordinate names so the field can be composed with the supplied parameterization. Surface flux is oriented by the parameter-order normal `r_u × r_v`.

Exact verification uses SymPy integration. Numeric claims additionally receive independent SciPy quadrature evidence by integrating the transformed integrand itself. The evidence is therefore independent of the exact symbolic result rather than merely re-integrating the answer.

This batch intentionally does not implement Green's theorem, the divergence theorem, or Stokes' theorem. Those theorem rules need their own orientation, boundary, regularity, and domain-contract checks and remain a later bounded batch.

Acceptance campaign: `tests/test_vector_calculus_integrals.py`.
