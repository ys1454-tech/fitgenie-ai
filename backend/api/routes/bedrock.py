"""
bedrock.py — Legacy verification routes for LLM service (migrated to Google Gemini).

Maintained for backward compatibility:
  GET  /api/bedrock/status — Inspect current LLM configuration and key presence
  POST /api/bedrock/test   — Perform an end-to-end diagnostic test with LLM provider
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from core.config import settings
from services.gemini_service import gemini_service

router = APIRouter(prefix="/bedrock", tags=["Bedrock (Migrated to Gemini)"])


class BedrockStatusResponse(BaseModel):
    configured: bool
    region: str
    model_id: str
    credentials_present: bool
    temperature: float
    max_tokens: int


class BedrockTestResponse(BaseModel):
    status: str
    configured: bool
    model_id: str
    region: str
    latency_ms: float | None = None
    response: str | None = None
    error_code: str | None = None
    message: str | None = None


@router.get("/status", response_model=BedrockStatusResponse)
def get_bedrock_status():
    """
    Check the LLM service configuration status.
    Returns status of the active LLM provider (Google Gemini).
    """
    has_creds = gemini_service.has_credentials_configured()
    return BedrockStatusResponse(
        configured=has_creds,
        region="global",
        model_id=settings.GEMINI_MODEL,
        credentials_present=has_creds,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


@router.post("/test", response_model=BedrockTestResponse)
def test_bedrock_connection(response: Response):
    """
    Test the end-to-end connection from FastAPI to LLM provider (Gemini).
    Returns 200 on success, or 503 with diagnostic details if credentials or access is missing.
    """
    result = gemini_service.test_connection()

    if result.get("status") != "success":
        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if result.get("error_code") in ("CREDENTIALS_MISSING", "MISSING_API_KEY")
            else status.HTTP_502_BAD_GATEWAY
        )

    return BedrockTestResponse(
        status=result.get("status", "error"),
        configured=result.get("configured", False),
        model_id=result.get("model", settings.GEMINI_MODEL),
        region="global",
        latency_ms=result.get("latency_ms"),
        response=result.get("response"),
        error_code=result.get("error_code"),
        message=result.get("message"),
    )
