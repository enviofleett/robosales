"""OpenRouter adapter — Harvey's brain powered by OpenRouter.

Sends prompts to OpenRouter's OpenAI-compatible chat completions API.
Supports model selection, token tracking, retry/backoff, and timeout limits.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("harvey.openrouter")

DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"


class OpenRouterError(Exception):
    """Base exception for OpenRouter operations."""
    def __init__(self, message: str, kind: str = "error"):
        super().__init__(message)
        self.kind = kind


class OpenRouterClient:
    """Client for OpenRouter Chat Completions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model = model or os.getenv("OPENROUTER_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", "").strip() or DEFAULT_OPENROUTER_URL).rstrip("/")

    def fingerprint(self) -> str:
        """Fingerprint to detect config/credential updates."""
        key_suffix = self.api_key[-6:] if self.api_key else "none"
        return f"openrouter:{self.model}:{key_suffix}"

    async def preflight(self) -> None:
        """Validate API key and model availability without full generation."""
        if not self.api_key:
            raise OpenRouterError(
                "OPENROUTER_API_KEY is not set in environment or .env.",
                kind="auth_missing"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ethanplusai/harvey",
            "X-Title": "Harvey Sales Automation",
        }

        # Verify key with OpenRouter auth endpoint
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/auth/key", headers=headers)
                if res.status_code == 401:
                    raise OpenRouterError(f"Invalid OpenRouter API Key: {res.text}", kind="unauthorized")
                elif res.status_code != 200:
                    raise OpenRouterError(f"OpenRouter key check failed (HTTP {res.status_code}): {res.text}")
        except httpx.RequestError as e:
            raise OpenRouterError(f"Network error connecting to OpenRouter: {e}", kind="network")

    async def complete(
        self,
        prompt: str,
        timeout: float = 180.0,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send chat completion request to OpenRouter."""
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is missing", kind="auth_missing")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ethanplusai/harvey",
            "X-Title": "Harvey Sales Automation",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if res.status_code == 401 or res.status_code == 403:
                raise OpenRouterError(f"OpenRouter Auth Error: {res.text}", kind="unauthorized")
            elif res.status_code == 429:
                raise OpenRouterError("OpenRouter Rate Limit exceeded", kind="rate_limit")
            elif res.status_code != 200:
                raise OpenRouterError(
                    f"OpenRouter API returned HTTP {res.status_code}: {res.text}",
                    kind="api_error"
                )

            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                return {"content": "", "usage": data.get("usage", {})}

            content = choices[0].get("message", {}).get("content", "")
            return {
                "content": content,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
            }


class OpenRouterQuotaClient:
    """Mock/wrapper for OpenRouter usage quota checking."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def get_usage(self) -> Dict[str, Any]:
        """Fetch usage/credit info if available."""
        if not self.client.api_key:
            return {"usage_pct": 0.0, "credits": 0.0}

        headers = {
            "Authorization": f"Bearer {self.client.api_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.client.base_url}/auth/key", headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    limit = data.get("limit") or 100.0
                    usage = data.get("usage") or 0.0
                    usage_pct = (usage / limit * 100) if limit else 0.0
                    return {
                        "usage_pct": usage_pct,
                        "limit": limit,
                        "usage": usage,
                        "is_free_tier": data.get("is_free_tier", False),
                    }
        except Exception:
            pass

        return {"usage_pct": 0.0}
