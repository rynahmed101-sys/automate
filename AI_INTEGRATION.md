# Automate AI Integration Architecture

Automate 0.2 introduces a dedicated, modular AI subsystem (`automate/ai/`) designed around a strict zero-trust boundary:

```
+-----------------------------------------------------------------------+
|                             AI Agent / LLM                            |
|             (Mock, Local llama.cpp/Ollama, OpenAI, Agent)             |
+-----------------------------------------------------------------------+
                                  |
               Emits automate.proposal.v1 JSON (Untrusted)
                                  v
+-----------------------------------------------------------------------+
|                     automate/ai/validation.py                         |
|  * Rejects eval(), exec(), os.system, shell metacharacters            |
|  * Rejects path traversal and secret leakage patterns                 |
|  * Rejects self-assigned verification statuses                        |
|  * Validates prerequisite input nodes and rule legality               |
+-----------------------------------------------------------------------+
                                  |
                                Valid
                                  v
+-----------------------------------------------------------------------+
|                      automate/ai/proposals.py                         |
|  * Clones graph (if dry_run=True)                                     |
|  * Injects candidate edge with status: "AI_PROPOSED"                  |
|  * Synthesizes verification obligations from RuleRegistry             |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                       Verification Backends                           |
|       SymPy        |       Lean 4       |       SciPy RK45            |
| (Symbolic Calculus)| (Formal Theorem)   | (Numerical IVP)             |
+-----------------------------------------------------------------------+
                                  |
                           Attaches Evidence
                                  v
+-----------------------------------------------------------------------+
|  Status Update: SYMBOLIC_CHECKED / FORMALLY_PROVED / FAILED           |
|  (Never automatically claims verified merely because AI proposed it)  |
+-----------------------------------------------------------------------+
```

---

## 1. Core Principles

1. **AI Proposes, Backends Verify**: An LLM is treated as a heuristic generator of mathematical hypotheses. An LLM cannot prove a theorem, confirm an equation of motion, or validate energy conservation by assertion.
2. **Zero Mandatory Cloud Dependencies**: The core system runs 100% offline. `MockLLMProvider` allows testing full AI interaction loops deterministically without network access or paid API keys.
3. **Provider Agnostic**: The abstract base class `LLMProvider` (`automate/ai/base.py`) decouples Automate from specific AI providers. Standard adapters exist for:
   - `MockLLMProvider`: Deterministic offline fixture.
   - `LocalLLMProvider`: Direct HTTP connection to local models (Ollama, LM Studio, llama.cpp, vLLM).
   - `OpenAIProvider`: Lightweight standard HTTP adapter using Python standard library `urllib` (zero mandatory third-party SDK dependencies).
4. **Pure Functional Proposals**: Proposals are declarative data dictionaries, never executable Python code or arbitrary scripts.

---

## 2. Directory Structure

```
automate/ai/
├── __init__.py           # Public exports and provider discovery
├── base.py               # Abstract LLMProvider interface
├── context.py            # Sanitized mathematical context generation
├── proposals.py          # Candidate edge injection and verification loop
├── schemas.py            # Pydantic models for proposals, context, candidate nodes
├── validation.py         # Security scanning and semantic validation
└── providers/
    ├── __init__.py
    ├── local.py          # Local model endpoint adapter (Ollama/LM Studio)
    ├── mock.py           # Deterministic test fixture provider
    └── openai.py         # Provider adapter for OpenAI-compatible APIs
```

---

## 3. Provider Discovery and Extension

Providers are discovered dynamically without failing if optional dependencies or keys are absent:

```python
from automate.ai import discover_available_providers, get_provider

# Check active providers
providers = discover_available_providers()
# {'mock': True, 'openai': False, 'local': False}

# Instantiate provider
prov = get_provider("mock")
assert prov.is_available() is True
```

### Implementing a Custom Provider

To add a new model provider (e.g. Anthropic, Gemini, Mistral), subclass `LLMProvider`:

```python
from automate.ai.base import LLMProvider
from typing import Dict, Any, Optional

class CustomProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "custom"

    def is_available(self) -> bool:
        return True

    def propose(
        self,
        context: Dict[str, Any],
        request: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Formulate prompt using context["equations"], context["available_rules"]
        # Call model endpoint
        # Return dictionary conforming to automate.proposal.v1 schema
        ...
```

---

## 4. Verification Status Transition Rules

When an AI proposes a derivation step:
1. **Initial Insertion**: The edge is assigned `VerificationStatus.AI_PROPOSED` (Rank 1).
2. **Pre-Checks**: Dimensional homogeneity is verified by `DimensionChecker`.
3. **Backend Execution**:
   - If SymPy proves algebraic equivalence: `VerificationStatus.SYMBOLIC_CHECKED`.
   - If Lean 4 verifies the formal proof script: `VerificationStatus.FORMALLY_PROVED`.
   - If SciPy ODE solver confirms trajectory within error tolerance: `VerificationStatus.NUMERICALLY_CHECKED`.
   - If statistical parameter estimation fits empirical data: `VerificationStatus.STATISTICALLY_CHECKED`.
   - If verification fails or raises an error: `VerificationStatus.FAILED`.
   - If side conditions / assumptions are inactive: `VerificationStatus.CONDITIONAL`.

Under no circumstances is an AI proposal marked as verified without backend evidence attached.
