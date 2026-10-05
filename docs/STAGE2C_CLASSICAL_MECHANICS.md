# Stage 2C Classical Mechanics Foundation

This branch establishes a reusable representation layer for classical mechanics. It does not claim the full Stage 2C roadmap.

## Representation

MechanicalSystemRepresentation captures generalized coordinates, kinetic and potential energy, generalized forces, constraints, parameters, assumptions, and time. The typed components make the structure explicit.

The representation composes into the existing LagrangianSystem rather than duplicating Euler-Lagrange machinery. This preserves the existing symbolic derivation and SymPy cross-check path.

## Current reusable operations

- kinematic first/second derivatives for arbitrary listed coordinates;
- canonical L = T - V and E = T + V construction;
- generalized-force mapping with unknown-coordinate rejection;
- explicit constraint residuals;
- conversion to the existing Euler-Lagrange/Hamiltonian/Noether engine.

## Existing mechanics before this branch

automate/mechanics/lagrangian.py already provides generalized-coordinate Lagrangian derivation, canonical momenta, Euler-Lagrange verification, Hamiltonian construction, energy-conservation verification, and a SymPy Euler-Lagrange cross-check. Existing tests cover harmonic oscillator, pendulum, central-force polar motion, coupled oscillators, free particle, and a relativistic free-particle cross-check.

Those are reusable primitives/examples, but the prior architecture lacked a canonical high-level mechanical-system representation.

## Deliberate boundaries

This branch does not claim implementation of all roadmap items: constraint enforcement with multipliers, general work/impulse integrals, Hamilton equation verification, Poisson brackets, canonical transformations, central-force/Kepler solution families, normal-mode diagonalization, rigid-body kinematics, or rotating-frame dynamics remain future capability work.

Malformed and structurally inconsistent representations fail closed rather than being inferred.
