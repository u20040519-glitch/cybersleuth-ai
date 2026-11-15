# =============================================================================
# CYBERSLEUTH AI - Gemini explanation layer (Phase 5)
# =============================================================================
# Gemini explains findings that the deterministic pipeline already produced.
# It is never the detection mechanism: every call receives a structured set of
# findings and must summarise them. If no API key is configured, or the call
# fails, the caller receives `available: false` with a reason and the UI keeps
# showing the structured findings without an AI narrative.
# =============================================================================

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a forensic analyst assistant for a digital evidence platform. "
    "You are given structured findings that were produced by deterministic "
    "analysis code. Explain them for an investigator in plain language. "
    "Rules: never invent a finding that is not in the input, never claim a "
    "conclusion that the data does not support, state uncertainty explicitly, "
    "and clearly separate what the data shows from what it might suggest. "
    "Respond with JSON only."
)


class GeminiClient:
    """Thin wrapper around the Gemini API with graceful degradation."""

    def __init__(self) -> None:
        self._configured = bool(settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_MODEL

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def model_name(self) -> str:
        return self._model_name

    async def explain(
        self,
        *,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Ask Gemini to explain a set of structured findings.

        Returns a dict with `available`, `text` and, when unavailable, a
        `reason` explaining why no explanation could be produced.
        """
        if not self._configured:
            return {
                "available": False,
                "reason": "GEMINI_API_KEY is not configured on this deployment.",
                "text": None,
                "model": self._model_name,
            }

        payload = {
            "prompt": prompt,
            "context": context or {},
        }

        try:
            text = await asyncio.to_thread(self._call_sync, payload)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini call failed: %s", exc)
            return {
                "available": False,
                "reason": f"The Gemini request failed: {exc}",
                "text": None,
                "model": self._model_name,
            }

        if not text:
            return {
                "available": False,
                "reason": "The Gemini model returned an empty response.",
                "text": None,
                "model": self._model_name,
            }

        return {
            "available": True,
            "reason": None,
            "text": text,
            "model": self._model_name,
        }

    def _call_sync(self, payload: dict[str, Any]) -> Optional[str]:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(self._model_name, system_instruction=SYSTEM_PROMPT)

        body = json.dumps(payload, default=str)[:12000]
        response = model.generate_content(
            f"{payload['prompt']}\n\nFindings (JSON):\n{body}",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 900,
                "response_mime_type": "application/json",
            },
        )
        return getattr(response, "text", None)


_client: Optional[GeminiClient] = None


def get_gemini() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


def reset_gemini() -> None:
    global _client
    _client = None
