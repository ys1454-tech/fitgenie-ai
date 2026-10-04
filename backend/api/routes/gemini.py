"""
gemini.py — Diagnostic and verification routes for Google Gemini service.

Endpoints:
  GET  /api/gemini/status — Inspect current configuration and API key presence
  POST /api/gemini/test   — Perform an end-to-end diagnostic test with Gemini
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from core.config import settings
from services.gemini_service import gemini_service

router = APIRouter(prefix="/gemini", tags=["Gemini"])


class GeminiStatusResponse(BaseModel):
    configured: bool
    model: str
    api_key_present: bool
    temperature: float
    max_tokens: int


class GeminiTestResponse(BaseModel):
    status: str
    configured: bool
    model: str
    latency_ms: float | None = None
    response: str | None = None
    error_code: str | None = None
    message: str | None = None


@router.get("/status", response_model=GeminiStatusResponse)
def get_gemini_status():
    """
    Check the Gemini service configuration status.
    Does not make an external network call.
    Never exposes the raw API key.
    """
    has_creds = gemini_service.has_credentials_configured()
    return GeminiStatusResponse(
        configured=has_creds,
        model=settings.GEMINI_MODEL,
        api_key_present=has_creds,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


@router.post("/test", response_model=GeminiTestResponse)
def test_gemini_connection(response: Response):
    """
    Test the end-to-end connection from FastAPI to Google Gemini.
    Sends a minimal verification prompt.
    Returns 200 on success, or 503 with diagnostic details if credentials or access is missing.
    """
    result = gemini_service.test_connection()

    if result.get("status") != "success":
        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if result.get("error_code") in ("CREDENTIALS_MISSING", "MISSING_API_KEY")
            else status.HTTP_502_BAD_GATEWAY
        )

    return GeminiTestResponse(**result)
