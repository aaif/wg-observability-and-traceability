"""Strict JSON Schema structured output from an OpenAI-compatible Chat Completions endpoint."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping

import httpx

from .common import JsonObject, require_secure_url


OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class ModelConfig:
    """Model settings read from the environment; the API key is hidden from repr."""

    api_key: str | None = field(default=None, repr=False)
    model: str | None = None
    base_url: str = OPENAI_BASE_URL

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ModelConfig:
        return cls(
            api_key=env.get("OPENAI_API_KEY") or None,
            model=env.get("OPENAI_MODEL") or None,
            base_url=env.get("OPENAI_BASE_URL") or OPENAI_BASE_URL,
        )

    def require(self) -> None:
        if not self.api_key or not self.model:
            raise ValueError("Set OPENAI_API_KEY and OPENAI_MODEL for model generation.")


class StructuredModelClient:
    """Request one schema-constrained JSON object; any refusal or truncation is an error."""

    def __init__(self, config: ModelConfig, client: httpx.AsyncClient):
        config.require()
        self.config = config
        self._client = client
        self._endpoint = config.base_url.rstrip("/") + "/chat/completions"
        require_secure_url(self._endpoint, "The model endpoint")

    async def complete(self, name: str, schema: JsonObject, system_prompt: str, user_content: str) -> Any:
        """Return the decoded JSON content; schema validation is left to the caller."""
        try:
            response = await self._client.post(
                self._endpoint, headers={"Authorization": f"Bearer {self.config.api_key}"}, json={
                    "model": self.config.model,
                    "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                })
        except httpx.HTTPError as error:
            raise ValueError(
                f"Model request failed ({type(error).__name__}); check network access and the configured endpoint."
            ) from None
        if not response.is_success:
            raise ValueError(f"Model request failed (HTTP {response.status_code}). Check model, context capacity, credentials, and structured-output support.")
        try:
            payload = response.json()
        except json.JSONDecodeError:
            raise ValueError("Model endpoint returned a non-JSON response; check OPENAI_BASE_URL.") from None
        choices = (payload.get("choices") or []) if isinstance(payload, dict) else []
        choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        message = choice.get("message") or {}
        if choice.get("finish_reason") != "stop" or message.get("refusal") or not message.get("content"):
            raise ValueError("Model refused, truncated, or returned no output; no partial JSON was emitted.")
        try:
            return json.loads(message["content"])
        except json.JSONDecodeError:
            raise ValueError("Model returned invalid JSON; no partial JSON was emitted.") from None
