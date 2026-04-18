"""
services/llm_client.py

Central LLM client for all agents. Uses the openai library pointed at
Groq's OpenAI-compatible endpoint. Swap base_url to use any other provider.
"""

import json
import time
import logging
from typing import Optional

from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Provider-agnostic LLM wrapper built on the openai library.

    Provides two public methods:
      - chat()      → plain text response  (used by all agents)
      - chat_json() → parsed dict response (used by scorer)

    Both support automatic retry on rate-limit errors.
    """

    DEFAULT_MODEL    = "llama-3.3-70b-versatile"
    DEFAULT_TEMP     = 0.7
    MAX_TOKENS       = 2048
    MAX_RETRIES      = 3
    RETRY_DELAY_SECS = 5
    BASE_URL         = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str, model: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is missing. Check your .env file.")
        self._client = OpenAI(
            api_key  = api_key,
            base_url = self.BASE_URL,
        )
        self.model = model or self.DEFAULT_MODEL
        logger.info(f"LLMClient initialised | model={self.model}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        system_prompt: str,
        user_message:  str,
        temperature:   float = DEFAULT_TEMP,
    ) -> str:
        """
        Send a chat completion and return the assistant reply as plain text.
        Used by all agents for natural language responses.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
        return self._call_with_retry(messages, temperature, json_mode=False)

    def chat_json(
        self,
        system_prompt: str,
        user_message:  str,
        temperature:   float = 0.2,
    ) -> dict:
        """
        Send a chat completion and return a parsed JSON dict.
        System prompt MUST instruct the model to return only valid JSON.
        Used by scorer.py only.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
        raw = self._call_with_retry(messages, temperature, json_mode=True)
        return self._parse_json(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        messages:    list[dict],
        temperature: float,
        json_mode:   bool,
    ) -> str:
        extra_kwargs = {}
        if json_mode:
            extra_kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model       = self.model,
                    messages    = messages,
                    temperature = temperature,
                    max_tokens  = self.MAX_TOKENS,
                    **extra_kwargs,
                )
                text = response.choices[0].message.content.strip()
                logger.debug(f"LLM OK [{attempt}/{self.MAX_RETRIES}]: {text[:120]}...")
                return text

            except RateLimitError:
                wait = self.RETRY_DELAY_SECS * attempt
                logger.warning(f"Rate limited. Retrying in {wait}s (attempt {attempt}/{self.MAX_RETRIES})")
                if attempt == self.MAX_RETRIES:
                    raise RuntimeError("Rate limit hit. All retries exhausted.")
                time.sleep(wait)

            except APIConnectionError as e:
                logger.error(f"Connection error: {e}")
                raise RuntimeError(f"Could not reach LLM API: {e}") from e

            except APIStatusError as e:
                logger.error(f"API error (status {e.status_code}): {e.message}")
                raise RuntimeError(f"LLM API returned an error: {e.message}") from e

        raise RuntimeError("_call_with_retry exhausted without returning.")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed. Raw response:\n{raw}")
            raise ValueError(f"Model returned invalid JSON: {e}") from e