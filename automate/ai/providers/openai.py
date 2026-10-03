"""
Optional OpenAI / GPT Provider Adapter.
Uses standard HTTP without mandatory third-party SDK dependencies.
Never exposes credentials in logs, exceptions, or graphs.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from automate.ai.base import LLMProvider
from automate.ai.schemas import DerivationProposal, ProposalOrigin


class OpenAIProvider(LLMProvider):
    """
    Adapter for OpenAI chat completions with structured JSON output.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1"
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key and len(self._api_key.strip()) > 0)

    def propose(
        self,
        context: Dict[str, Any],
        request: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("OpenAIProvider is unavailable: OPENAI_API_KEY is not configured.")

        opts = options or {}
        model = opts.get("model", self._model)
        timeout = opts.get("timeout", 30)

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
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content_str = res_json["choices"][0]["message"]["content"]
                parsed_proposal = json.loads(content_str)

                # Inject secure origin provenance (never with API key)
                parsed_proposal["origin"] = ProposalOrigin(
                    type="ai",
                    provider=self.name,
                    model=model,
                    context_hash=context.get("graph_hash")
                ).model_dump()

                return parsed_proposal
        except Exception as e:
            # Strip potential key leak from error representation
            sanitized_err = str(e).replace(self._api_key or "", "[REDACTED]")
            raise RuntimeError(f"OpenAI proposal request failed: {sanitized_err}") from None
