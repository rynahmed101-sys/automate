# Automate Project Operations

## 🌱 Mission

Automate is built to make difficult mathematical reasoning more machine-checkable, auditable, and understandable.

The working environment should feel constructive: every large goal becomes a small verified step, every limitation is documented rather than hidden, and every successful check becomes reusable infrastructure.

## 🧭 Working loop

1. **Observe** the current repository state.
2. **Choose one bounded objective.**
3. **Implement the smallest useful change.**
4. **Test adversarially.**
5. **Record what is actually verified.**
6. **Keep the next step visible.**

## 🗂️ GitHub workspace model

Use GitHub as the project control plane:

- **Issues** = individual problems, experiments, research questions, and bounded tasks.
- **Projects** = the visual roadmap and work queue.
- **Pull requests** = reviewable implementation units.
- **Actions** = automated verification.
- **Wiki / long-form documentation** = architecture and operator knowledge when the account/repository plan supports it.
- **Repository docs** = versioned specifications and permanent technical contracts.
- **Releases** = stable milestones.
- **Discussions** = design conversations when enabled and useful.

## 📌 Project board structure

Recommended views:

### Now
Work that is actively being implemented.

### Next
Small, clearly defined tasks ready to start.

### Research
Questions that need investigation before implementation.

### Verification
Test, proof, provenance, adversarial, and cross-engine work.

### Done
Completed and verified work.

Suggested fields:

- Status
- Priority
- Area
- Verification state
- Milestone
- Next step

Suggested status vocabulary:

🌱 Idea → 🧭 Planned → 🔨 Building → 🧪 Verifying → ✅ Verified → 📦 Released

The emojis are intentionally boringly cheerful. Software development has enough red error text.

## 🔬 Verification rule

Never promote a claim because it sounds plausible.

Use explicit states:

- **Implemented**: code exists.
- **Tested**: automated tests exercise it.
- **CI verified**: the authoritative workflow passed.
- **Independent agreement**: another engine or independently generated result agrees.
- **Formally proved**: a sound formal prover establishes the claim.

These states must never be silently collapsed into one another.

## 🔐 Security rule

Private repository status is a workspace boundary, not a substitute for security engineering.

Secrets never belong in issues, commits, logs, examples, or certificates. External engines remain bounded and provenance-bound. Unsupported semantics fail closed.

## 🌤️ Project culture

The goal is not artificial optimism. It is useful optimism:

- small progress counts;
- failed tests are information;
- unknown is better than falsely verified;
- documentation prevents future confusion;
- boring infrastructure is valuable;
- every finished boundary makes the next boundary easier.

