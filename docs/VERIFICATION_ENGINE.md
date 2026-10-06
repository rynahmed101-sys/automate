# Verification & Reconciliation Engine

The Verification & Reconciliation Engine is a logical subsystem distributed
across Automate, Chanfana, and THE MIRROR.

Automate owns canonical scientific semantics and authority. Chanfana owns
durable execution, transport, leases, retries, and persistence. THE MIRROR
owns bounded laboratory execution. The verifier coordinates evidence and
reasoning but cannot certify or promote a capability.

## Implemented control path

1. Exact-revision verification intake.
2. Live repository inventory and claim-vs-observation reconciliation.
3. Competing failure diagnosis.
4. Automate mathematical verification.
5. Bounded repair planning with protected authority/security paths.
6. Append-only evidence receipts linked by parent IDs.
7. Bounded Mirror verification commissioning.
8. Exact-head CI and security evidence classification.
9. Explicit evidence-state transitions.
10. Verifiable evidence packet construction and consistency checks.
11. Automate-side promotion gate.
12. CI self-test against the installed Stage 1A-3A backlog.
13. Bearer-protected /verification/v1/requests service for Chanfana handoff.

## Authority rule

Packets are evidence only. They are not instructions to promote.
A capability becomes authoritative only through Automate's existing promotion
and certification controls on the exact merged main revision.

## First production workload

docs/VERIFICATION_BACKLOG.json installs the real 1A-3A capability frontier.
The first workload is stage1b.improper_integrals (Issue #115), not a synthetic
demo.

When the Mirror endpoint is unavailable, the packet records the missing
laboratory evidence rather than inventing an experiment ID.

## Cross-repository boundary

Chanfana can POST an exact-revision request to /verification/v1/requests.
The service is bearer-token protected, has bounded request/response sizes, and
does not merge, certify, or mutate authority.

THE MIRROR receives bounded scientific experiment requests and returns
observations plus provenance. It does not certify.
