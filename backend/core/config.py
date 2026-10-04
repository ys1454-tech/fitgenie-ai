"""
config.py — Application configuration for FitGenie AI.
Reads settings from the .env file using python-dotenv.
Real credentials must NEVER be hardcoded here.
"""

import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()


class Settings:
    """Holds all application configuration values."""

    # Google Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Legacy AWS / Amazon Bedrock settings (retained for backward compatibility)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_SESSION_TOKEN: str = os.getenv("AWS_SESSION_TOKEN", "")
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "")

    # LLM generation settings
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Application settings
    APP_NAME: str = "FitGenie AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Frontend origin for CORS
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")


# Single shared instance — import this wherever settings are needed
settings = Settings()
