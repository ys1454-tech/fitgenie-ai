"""
gemini_service.py — Google Gemini LLM client service for FitGenie AI.

Responsibilities:
  - Initialize the official Google GenAI SDK client using environment configuration.
  - Proxy all LLM calls through the backend (never exposing API keys to the frontend/logs).
  - Handle Gemini API errors, missing credentials, timeouts, and rate limits gracefully.
  - Provide structured output and test connection utilities.
"""

import logging
import time
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from core.config import settings

logger = logging.getLogger(__name__)

# Map retired/deprecated model names to modern replacements
MODEL_ALIASES = {
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "models/gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.5-flash": "gemini-3.5-flash",
    "models/gemini-2.5-flash": "gemini-3.5-flash",
}


class GeminiServiceError(Exception):
    """Base exception for Gemini service failures."""

    def __init__(self, message: str, error_code: str = "GEMINI_ERROR", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class GeminiService:
    """Service wrapper for Google Gemini API interactions."""

    def __init__(self):
        self.model = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.default_temperature = settings.LLM_TEMPERATURE
        self.default_max_tokens = settings.LLM_MAX_TOKENS
        self._client = None

    def _resolve_model(self) -> str:
        """Resolve model name, applying aliases if a deprecated model is requested."""
        configured_model = settings.GEMINI_MODEL or self.model
        return MODEL_ALIASES.get(configured_model, configured_model)

    def has_credentials_configured(self) -> bool:
        """
        Check if the Gemini API key is configured.
        Never reveals the key content.
        """
        key = settings.GEMINI_API_KEY
        if not key:
            return False
        # Ensure it's not a template placeholder
        if "your_gemini" in key.lower():
            return False
        return bool(key.strip())

    def get_client(self) -> genai.Client:
        """
        Get or initialize the Google GenAI client.
        """
        if self._client is not None:
            return self._client

        if not self.has_credentials_configured():
            raise GeminiServiceError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env.",
                error_code="MISSING_API_KEY",
            )

        try:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            return self._client
        except Exception as exc:
            logger.error("Failed to initialize Google GenAI client: %s", exc)
            raise GeminiServiceError(
                f"Failed to initialize Google GenAI client: {exc}",
                error_code="CLIENT_INIT_FAILED",
            ) from exc

    def invoke(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_mime_type: str | None = None,
    ) -> str:
        """
        Send a prompt to Google Gemini API and return the raw text output.

        Args:
            user_prompt: Main prompt content.
            system_prompt: Optional system prompt instructions.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum output tokens in generated response.
            response_mime_type: Optional MIME type (e.g. 'application/json').

        Returns:
            Raw generated text from the LLM.

        Raises:
            GeminiServiceError with descriptive error message and code.
        """
        if not self.has_credentials_configured():
            raise GeminiServiceError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env.",
                error_code="MISSING_API_KEY",
            )

        client = self.get_client()
        model_name = self._resolve_model()

        temp = temperature if temperature is not None else self.default_temperature
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        config_kwargs: dict[str, Any] = {
            "temperature": float(temp),
            "max_output_tokens": int(tokens),
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }

        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        try:
            logger.info("Calling Google Gemini model: %s", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )

            if not response.text:
                raise GeminiServiceError(
                    "Gemini returned an empty response.",
                    error_code="EMPTY_RESPONSE",
                )

            return response.text

        except APIError as exc:
            error_code = str(exc.code) if exc.code else "API_ERROR"
            error_msg = exc.message or str(exc)
            logger.error("Gemini APIError [%s]: %s", error_code, error_msg)

            if "NOT_FOUND" in error_msg or exc.code == 404:
                message = f"Gemini model '{model_name}' was not found or is unavailable: {error_msg}"
            elif "PERMISSION_DENIED" in error_msg or exc.code == 403:
                message = "Gemini API permission denied. Check your GEMINI_API_KEY validity and permissions."
            elif "RESOURCE_EXHAUSTED" in error_msg or exc.code == 429:
                message = "Gemini API rate limit or quota exceeded. Please wait a moment before trying again."
            else:
                message = f"Google Gemini API error ({error_code}): {error_msg}"

            raise GeminiServiceError(
                message=message,
                error_code=error_code,
                details={"api_message": error_msg},
            ) from exc

        except Exception as exc:
            logger.error("Unexpected error invoking Gemini: %s", exc)
            raise GeminiServiceError(
                f"Unexpected error while communicating with Gemini: {exc}",
                error_code="UNEXPECTED_ERROR",
            ) from exc

    def test_connection(self) -> dict:
        """
        Run a lightweight diagnostic ping against Google Gemini API.
        Returns a dictionary with status, latency, model info or error details.
        """
        if not self.has_credentials_configured():
            return {
                "status": "error",
                "configured": False,
                "error_code": "CREDENTIALS_MISSING",
                "message": "Gemini API key is not configured. Add your GEMINI_API_KEY to backend/.env.",
                "model": self.model,
            }

        model_name = self._resolve_model()
        start_time = time.time()
        try:
            test_prompt = "Reply strictly with JSON: {\"status\": \"ok\", \"service\": \"gemini\"}"
            raw_response = self.invoke(
                user_prompt=test_prompt,
                system_prompt="Respond strictly with the requested JSON.",
                max_tokens=60,
                temperature=0.0,
                response_mime_type="application/json",
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "success",
                "configured": True,
                "model": model_name,
                "latency_ms": elapsed_ms,
                "response": raw_response.strip(),
            }
        except GeminiServiceError as err:
            return {
                "status": "error",
                "configured": True,
                "error_code": err.error_code,
                "message": err.message,
                "details": err.details,
                "model": model_name,
            }
        except Exception as exc:
            return {
                "status": "error",
                "configured": True,
                "error_code": "TEST_FAILED",
                "message": str(exc),
                "model": model_name,
            }


# Shared singleton instance
gemini_service = GeminiService()
