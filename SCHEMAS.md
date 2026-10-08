# Automate Schemas

Automate uses machine-readable schemas where they make interchange easier.

The most important contract is the mathematical data/IR representation. Calculator operations should remain simple and stable.

## Core schemas

- `schemas/automate-ir-v0.1.json`: canonical mathematical/physics representation
- `schemas/automate-tensor-v1.json`: tensor interchange
- `schemas/automate-capability-inventory-v1.json`: internal capability inventory

The former AI proposal, AI context, agent-control and certificate-package schemas are retired from the public calculator interface.

## Calculator principle

An AI should not need to manufacture a proposal object, obtain an approval status, or construct a certificate package just to ask Automate to calculate something.

The preferred interaction is:

```
request
→ calculation
→ result
```

Optional diagnostics may accompany the result when useful.
