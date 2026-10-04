"""
bedrock_service.py — Compatibility layer aliasing to Google Gemini service.
The FitGenie AI LLM integration was migrated from Amazon Bedrock to Google Gemini.
This module preserves backwards compatibility with any existing imports.
"""

from services.gemini_service import (
    GeminiService,
    GeminiServiceError,
    gemini_service,
)

# Compatibility aliases
BedrockService = GeminiService
BedrockServiceError = GeminiServiceError
bedrock_service = gemini_service

__all__ = [
    "BedrockService",
    "BedrockServiceError",
    "bedrock_service",
    "GeminiService",
    "GeminiServiceError",
    "gemini_service",
]
