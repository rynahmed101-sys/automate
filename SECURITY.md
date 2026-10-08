# Automate Security

Automate accepts mathematical data that may originate from untrusted AI output, users or external files.

Security therefore concerns **execution safety**, not scientific permission.

## Required protections

The calculator must:

- never execute arbitrary Python supplied as mathematical text
- never execute shell commands from mathematical input
- never allow mathematical input to become an arbitrary filesystem operation
- enforce reasonable parser/resource limits
- isolate genuinely unsafe subprocess work
- return clear computational errors instead of executing unexpected operations

The safe mathematical parser is the primary boundary for symbolic expressions.

## Scientific openness

Security rules must not be confused with restrictions on mathematics or physics.

An unconventional equation is not a security violation.

A hypothetical physical model is not a security violation.

A mathematically strange expression is not a security violation.

If the expression is safely representable and the requested operation is supported, Automate should calculate it.

## Reporting

Actual software vulnerabilities should be reported through the repository's normal security reporting mechanism.
