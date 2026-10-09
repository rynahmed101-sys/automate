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
- limits and Taylor/series expansions, with configurable center and SymPy order
  semantics (terms below the requested order plus an Order term)
- multivariable derivatives, total differentials, Jacobians, Hessians, and stationary-point candidates
- Cartesian divergence, curl, and Laplacian
- symbolic stationary-point candidates for optimization workflows
- symbolic PDE solving for equation classes supported by SymPy
- numeric unit conversion, descriptive statistics, and allowlisted SciPy distributions
- linear algebra
- vectors, tensors and geometry
- numerical mathematics
- ordinary and partial differential equations
- lower-level mechanics and electromagnetism representations
- tensor and geometric calculations through the graph/IR and Python backends
- general symbolic and numerical calculations for user-supplied physics
  expressions; this is not a claim of complete domain-specific workflows

The engine should calculate an unusual equation just as readily as a familiar one. It does not decide whether an idea is fashionable, established or physically true.

## Direct use

The calculator is available both as a Python API and through the CLI. The Python API keeps ordinary mathematical expressions and objects intact:

```python
from automate import calculate

calculate("differentiate", "x**2*y", variable="x")
calculate("matrix_determinant", "Matrix((1,2),(3,4))")
calculate("ode_solve", "diff(y(x), x) = y(x)", dependent_variable="y", independent_variable="x")
calculate("transform", "exp(2*t)", variable="t", transform_type="laplace", transform_variable="s")
calculate("stationary_points", "(x-2)**2 + 3", variables=["x"])
calculate("unit_convert", "1", source_unit="km", target_unit="m")
calculate("descriptive_statistics", [1, 2, 3, 4])
calculate("distribution", "0", distribution_name="normal", distribution_function="pdf")
calculate("pde_solve", "diff(u(x,y), x) + diff(u(x,y), y) = 0")
calculate("total_differential", "x**2*y", variables=["x", "y"])
calculate("curl", "Matrix((y, z, x))", variables=["x", "y", "z"])
```

The `calculate` CLI exposes the same operation arguments, including definite
integral bounds, equation arrays, transform options, and the recovered unit and
distribution arguments:

`automate calculate --operation differentiate --expression "x**2*y" --variable x`

`automate calculate --operation integrate_definite --expression "x**2" --variable x --lower 0 --upper 3 --json`

`automate calculate --operation series --expression "exp(x)" --variable x --point 1 --order 4 --json`

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

The response includes the familiar readable `result` plus a typed `result_data` representation for matrices, symbolic expressions, sequences, mappings, and physical quantities. Existing `calculate --json` output retains its readable result and adds the typed representation. Invalid JSON-mode calculations return a nonzero process status as well as a machine-readable error. Verification remains optional; malformed requests and unsupported operations return clear errors.

## Use Automate from GitHub Actions

This public repository also provides a composite GitHub Action. An AI agent or
workflow can call it directly without an Automate API key or other Automate
credentials:

```yaml
steps:
  - id: calculate
    uses: rynahmed101-sys/automate@main
    with:
      request: |
        {"operation":"differentiate","expression":"x**2*y","variable":"x"}
  - name: Use the result
    env:
      AUTOMATE_RESULT: ${{ steps.calculate.outputs.result }}
    run: printf '%s\n' "$AUTOMATE_RESULT"
```

The action exposes `response` (full JSON), `result` (readable result), and
`result_data` (typed JSON) outputs. It installs Automate from the checked-out
public action source and runs the same `automate request` interface shown above;
an invalid request fails the action. For production workflows, pin `uses` to a
reviewed commit SHA instead of the moving `main` branch.

This is an execution action, not an anonymously hosted API: GitHub runs it in a
workflow/runner controlled by the caller, and the caller's normal GitHub
workflow permissions and trigger requirements still apply. Automate itself
requires no credentials.

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
