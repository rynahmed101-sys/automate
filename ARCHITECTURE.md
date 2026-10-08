# Automate Architecture

Automate is a mathematics and physics calculation engine intended to be called by AI systems.

## Boundary

```
AI
  |
  | interprets request
  v
structured calculation request
  |
  v
Automate
  |
  +--> safe mathematical parsing
  +--> symbolic backend
  +--> numerical backend
  +--> linear algebra
  +--> vectors / tensors / geometry
  +--> physics backends
  |
  v
calculation result
  |
  v
AI interprets result
```

Automate is not an autonomous AI, research agent, coding agent, or scientific approval authority.

## Core layers

### Input

Structured requests and mathematical data enter through the CLI or Python API.

### Representation

The existing IR provides reusable representations for expressions, vectors, matrices, tensors, dimensions, equations and physical structures.

### Calculation

Backends perform the requested operation. Existing scientific libraries are reused rather than unnecessarily reimplemented.

### Optional diagnostics

Some operations can provide dimensional checks, numerical residuals, symbolic comparisons, assumptions or other diagnostics. These are additional information, not universal permission gates.

### Output

Results should be simple, machine-readable and usable by the calling AI.

## Security boundary

Security remains important for untrusted input. The mathematical parser must not execute arbitrary Python, shell commands or filesystem operations merely because an expression was supplied by an AI.

This is a software safety boundary, not a scientific legitimacy boundary.

## Extensibility

A new capability should normally follow:

**existing backend → thin Automate interface → focused test → useful machine output**

Do not create a new reasoning framework when a backend operation already solves the problem.

## Documentation authority

Use `docs/AUTOMATE_SCIENTIFIC_ENGINE_LEDGER.md` for project direction.

Do not maintain competing roadmaps or AI control-plane manuals.
