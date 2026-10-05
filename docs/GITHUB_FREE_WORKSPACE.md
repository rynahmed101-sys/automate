# GitHub Free Workspace

Automate uses the public GitHub repository as its collaborative engineering boundary. The goal is to use GitHub features as infrastructure without weakening mathematical verification discipline.

## Workspace map

- Issues: bounded engineering tasks, research questions, verification failures, and security findings.
- Projects: visual planning and queue management.
- Pull requests: small, reviewable implementation boundaries.
- Actions: automated test and proof checks. A queued run is never described as green.
- Releases: stable milestones and externally meaningful snapshots.
- Discussions: design conversations when enabled for the repository.
- Wiki: long-form navigational documentation when available on the repository plan. Permanent technical contracts remain in docs/ so they are versioned with the code.
- Dependabot: dependency and GitHub Actions update proposals.
- Codespaces / dev container: reproducible development environment for contributors.

## Project status vocabulary

🌱 Idea → 🧭 Planned → 🔨 Building → 🧪 Verifying → ✅ Verified → 📦 Released

## Verification vocabulary

- Implemented: code exists.
- Tested: local or CI tests exercised the behavior.
- CI verified: the authoritative GitHub Actions run completed successfully for the relevant commit.
- Independent agreement: an independent computation or verification path agrees.
- Formally proved: a formal proof backend establishes the claim.

These states are not interchangeable.

## Public-repository security rule

Public visibility is intentional. Never put secrets, credentials, private keys, tokens, or sensitive personal data in issues, pull requests, logs, examples, commits, or test fixtures. Public infrastructure is not a substitute for application-level security boundaries.

External engines remain bounded and provenance-bound. Unsupported semantics fail closed.

## Recommended Project views

- Now: active implementation and verification.
- Next: ready work.
- Research: experiments and future capabilities.
- Verification: CI, adversarial tests, provenance, and independent checks.
- Done: completed work.

Recommended fields: Status, Priority, Area, Verification state, Milestone, Next step.

## Working principle

Build carefully. Verify honestly. Keep the next step visible. Small, independently verified improvements compound.
