# Autonomous Self-Correction and Rectification

Automate treats failure as a control event, not as permission to guess.

## Required behavior

1. Exact-head CI/Security failure is retried only once for the same immutable worker SHA.
2. A repeated failure is diagnosed and the worker PR is quarantined without promotion.
3. The failed capability enters `REPAIR_HOLD`; the original task must not be re-dispatched while repair is unresolved.
4. Automatic rectification uses a new repair generation and deterministic request/branch identity, for example `-repair2` then `-repair3`.
5. Closed, unmerged quarantined worker PRs act as a durable hold signal across control-cycle invocations.
6. A repair remains untrusted until it passes exact-head verification, scientific-evidence checks, promotion, and post-merge gates.
7. Repair success clears the operational hold by normal lifecycle progression; no manual certification shortcut exists.
8. Control-plane uncertainty fails closed and may keep the system stopped or held while the defect is repaired.

## Authority boundary

Backlink Vault supplied useful engineering patterns for a continuously running worker, bounded settings, and an audit log. Those patterns are inspiration only. Automate does not inherit Backlink Vault's application-level trust model, scraping behavior, or deployment assumptions.

Automate remains the mathematical and scientific authority. Mirror remains the experimental reasoning and research lab. Chanfana remains bounded durable transport.
