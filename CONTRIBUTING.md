# Contributing to Automate

We welcome contributions to Automate!

## Guiding Principles
* **Do not invent new CAS or theorem provers**: Wrap and interoperate with mature open-source tools (Lean 4, Mathlib, Physlib, SymPy, SciPy).
* **Assumptions are first-class**: Never discard physical assumptions silently.
* **Lossless macro-expansion**: Support high-level physics steps without losing intermediate verification certificates.
* **Local-first**: All verification features must function without external or proprietary APIs.

## Pull Request Checklist
1. All unit tests pass: `pytest tests/ -v`.
2. End-to-end physics demo succeeds: `automate demo`.
3. Clear documentation and type annotations provided for all new classes and methods.
