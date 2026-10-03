"""
Base abstraction for AI proposal providers.
Automate core NEVER depends on any single external LLM provider.
All providers are optional adapters returning structured proposal dictionaries.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """
    Abstract base provider for mathematical derivation proposal generators.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'mock', 'openai', 'local'."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and reachable."""
        pass

    @abstractmethod
    def propose(
        self,
        context: Dict[str, Any],
        request: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates a structured mathematical proposal dictionary conforming to automate.proposal.v1.
        Must NOT execute code or modify the graph directly.
        """
        pass
