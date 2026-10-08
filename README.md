# Automate

> **Local-first mathematics and physics calculator for AI systems**

Automate is a computational workbench that gives an AI direct access to mathematical and physics operations without making Automate itself responsible for interpreting the problem.

The boundary is simple:

**AI interprets the problem → Automate calculates → AI interprets the result.**

Automate uses mature scientific libraries where appropriate, including SymPy, NumPy, SciPy, EinsteinPy and related tools.

## What it does

Automate provides reusable operations for:

- arithmetic and algebra
- symbolic simplification
- equations and solving
- derivatives and integrals
- limits and series
- multivariable mathematics
- linear algebra
- vectors, tensors and geometry
- numerical mathematics
- ordinary and partial differential equations
- mechanics
- electromagnetism
- thermodynamics and statistics
- quantum and relativistic mathematics
- broader mathematical physics

The engine should calculate an unusual equation just as readily as a familiar one. It does not decide whether an idea is fashionable, established or physically true.

## Direct use

The CLI exposes a small direct calculator interface:

`automate calculate --operation differentiate --expression "x**2*y" --variable x`

Machine-readable output:

`automate calculate --operation integrate --expression "2*x" --variable x --json`

More operations are exposed as the underlying backends support them.

## AI integration

An external AI can call Automate as a tool. Automate does not contain an internal LLM controller, proposal loop, research agent or provider manager.

The AI owns:

- natural-language interpretation
- choosing useful operations
- combining results
- scientific interpretation
- hypothesis generation

Automate owns:

- mathematical representation
- computation
- numerical execution
- optional calculation diagnostics
- safe parsing of untrusted mathematical input

## Design rule

Do not add bureaucracy where a calculator operation is sufficient.

Verification, assumptions, dimensions, provenance and formal proof can remain available as useful tools for cases that need them. They are not permission gates for ordinary calculation.

## Development

The authoritative operating ledger is:

`docs/AUTOMATE_SCIENTIFIC_ENGINE_LEDGER.md`

The project should grow by adding useful reusable calculator operations and exposing existing backend capabilities through simple machine-friendly interfaces.

## License

Apache-2.0.
