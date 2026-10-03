"""
Local LLM Provider Adapter for OpenAI-compatible local inference endpoints
(Ollama, LM Studio, llama.cpp, LocalAI, vLLM).
Works completely offline against local network addresses.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from automate.ai.base import LLMProvider
from automate.ai.schemas import ProposalOrigin


class LocalLLMProvider(LLMProvider):
    """
    Adapter for local LLM engines exposing an OpenAI-compatible /v1/chat/completions endpoint.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3:latest",
        timeout: int = 30
    ):
        self._base_url = (base_url or os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1")).rstrip("/")
        self._model = os.environ.get("LOCAL_LLM_MODEL", model)
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "local"

    def is_available(self) -> bool:
        """
        Pings local endpoint models list to determine availability.
        """
        try:
            req = urllib.request.Request(f"{self._base_url}/models", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def propose(
        self,
        context: Dict[str, Any],
        request: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        opts = options or {}
        model = opts.get("model", self._model)
        timeout = opts.get("timeout", self._timeout)

        system_prompt = (
            "You are a mathematical physics derivation assistant for Automate. "
            "Given a mathematical context and request, propose the next formal derivation step. "
            "You must return ONLY a JSON object conforming strictly to schema 'automate.proposal.v1'. "
            "Never include Markdown formatting or code blocks outside the JSON."
        )

        user_content = (
            f"Mathematical Context:\n{json.dumps(context, indent=2)}\n\n"
            f"User Goal / Request:\n{request}\n\n"
            "Propose the next derivation transformation rule, input node IDs, output node expressions, "
            "and required assumptions or side conditions."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": opts.get("temperature", 0.0)
        }

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content_str = res_json["choices"][0]["message"]["content"]
                parsed_proposal = json.loads(content_str)

                parsed_proposal["origin"] = ProposalOrigin(
                    type="ai",
                    provider=self.name,
                    model=model,
                    context_hash=context.get("graph_hash")
                ).model_dump()

                return parsed_proposal
        except Exception as e:
            raise RuntimeError(f"Local LLM proposal request to '{self._base_url}' failed: {e}") from None
