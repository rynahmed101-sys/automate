# Autonomous Self-Correction and Rectification

Automate treats failure as a control event, not as permission to guess.

## Required behavior

1. Exact-head CI/Security failure is retried only once for the same immutable worker SHA.
2. A repeated failure is diagnosed and the worker PR is quarantined without promotion.
3. The failed capability enters `REPAIR_HOLD`; the original task must not be re-dispatched while repair is unresolved.
4. Automatic rectification uses a new repair generation and deterministic request/branch identity (for example `-repair2`, then `-repair3`).
5. Closed, unmerged quarantined worker PRs act as a durable hold signal across control-cycle invocations.
6. Repair workers may be commissioned through Mirror, the generic bounded worker, or another explicitly supported execution route. Worker output remains untrusted.
7. A repair remains untrusted until it passes exact-head verification, scientific evidence checks, promotion, and post-merge gates.
8. Successful repair clears the operational hold only through normal lifecycle progression. There is no manual certification shortcut.
9. Control-plane uncertainty fails closed and may keep the system stopped or held while the defect is repaired.
10. Chanfana persists the repair job, result, and relevant learning experience so later cycles can reuse failure knowledge.
11. Mirror may research, code, experiment, diagnose, and repair during backlog clearing and later discovery. Its implementation output is a proposal/evidence package, not authority.

## Authority boundary

Automate owns canonical mathematical semantics, capability ordering, acceptance, promotion, and certification.

Mirror is the autonomous AI engineering, research, diagnostic, repair, and scientific execution partner. It can do the work but cannot certify or promote itself.

Chanfana is the durable execution and memory substrate. It transports jobs, manages leases/recovery, stores learning artifacts, and preserves provenance. It does not decide scientific truth.

External engineering patterns such as the Backlink Vault worker loop are inspiration only. Automate does not inherit unrelated trust models, scraping behavior, or deployment assumptions.
