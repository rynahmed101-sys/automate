"""
Automate AI Subsystem: Universal AI compatibility, structured proposals, and verification loops.
"""

from typing import Optional, Dict

from automate.ai.base import LLMProvider
from automate.ai.schemas import DerivationProposal, CandidateNode, AIContext, ProposalOrigin
from automate.ai.validation import validate_ai_proposal, ProposalValidationResult
from automate.ai.context import build_ai_context, compute_semantic_graph_hash
from automate.ai.proposals import apply_and_verify_proposal, ProposalExecutionResult
from automate.ai.providers.mock import MockLLMProvider
from automate.ai.providers.openai import OpenAIProvider
from automate.ai.providers.local import LocalLLMProvider


def get_provider(name: str = "mock", **kwargs) -> LLMProvider:
    """
    Factory function returning the requested AI provider adapter.
    """
    prov_lower = name.lower()
    if prov_lower == "mock":
        return MockLLMProvider(**kwargs)
    elif prov_lower == "openai":
        return OpenAIProvider(**kwargs)
    elif prov_lower == "local":
        return LocalLLMProvider(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider '{name}'. Choose from: 'mock', 'openai', 'local'.")


def discover_available_providers() -> Dict[str, bool]:
    """
    Discovers which providers are currently configured and reachable.
    """
    return {
        "mock": MockLLMProvider().is_available(),
        "openai": OpenAIProvider().is_available(),
        "local": LocalLLMProvider().is_available()
    }


__all__ = [
    "LLMProvider",
    "DerivationProposal",
    "CandidateNode",
    "AIContext",
    "ProposalOrigin",
    "validate_ai_proposal",
    "ProposalValidationResult",
    "build_ai_context",
    "compute_semantic_graph_hash",
    "apply_and_verify_proposal",
    "ProposalExecutionResult",
    "MockLLMProvider",
    "OpenAIProvider",
    "LocalLLMProvider",
    "get_provider",
    "discover_available_providers"
]
