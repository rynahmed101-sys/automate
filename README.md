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
- symbolic ordinary differential-equation solving
- Laplace and Fourier transforms, including inverse transforms
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

The calculator is available both as a Python API and through the CLI. The Python API keeps ordinary mathematical expressions and objects intact:

```python
from automate import calculate

calculate("differentiate", "x**2*y", variable="x")
calculate("matrix_determinant", "Matrix((1,2),(3,4))")
calculate("ode_solve", "diff(y(x), x) = y(x)", dependent_variable="y", independent_variable="x")
calculate("transform", "exp(2*t)", variable="t", transform_type="laplace", transform_variable="s")
```

The CLI provides the same calculator surface for shell tools and AI agents:

`automate calculate --operation differentiate --expression "x**2*y" --variable x`

Machine-readable output:

`automate calculate --operation integrate --expression "2*x" --variable x --json`

Use `automate capabilities --json` to discover the currently exposed operations. The interface is intentionally thin: mathematical expressions, symbolic objects, and safe constructors remain available instead of being hidden behind a specialized protocol.

## Structured AI requests

The Python API keeps native SymPy objects intact and also accepts a mapping-shaped request. Call `calculator_manifest()` to discover operation names, descriptions, and argument requirements:

```python
from automate import calculate_request, calculator_manifest

manifest = calculator_manifest()
result = calculate_request({
    "operation": "differentiate",
    "expression": "x**2*y",
    "variable": "x",
})
```

For shell tools and process-based agents, send a JSON request on standard input or use `--request-json`:

```sh
echo '{"operation":"matrix_determinant","expression":"Matrix((1,2),(3,4))}' | automate request
```

The response includes the familiar readable `result` plus a typed `result_data` representation for matrices, symbolic expressions, sequences, and mappings. Existing `calculate --json` output retains its readable result and adds the typed representation. Verification remains optional; malformed requests and unsupported operations return clear errors.

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
