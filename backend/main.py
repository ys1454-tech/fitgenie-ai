"""
main.py — FitGenie AI FastAPI application entry point.

Starts the FastAPI server, registers all API routes,
and configures CORS so the React frontend can communicate with it.
Database tables are created automatically on startup via the lifespan event.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database.db import init_db
from api.routes.health import router as health_router
from api.routes.sessions import router as sessions_router
from api.routes.plans import router as plans_router
from api.routes.coach import router as coach_router
from api.routes.gemini import router as gemini_router
from api.routes.bedrock import router as bedrock_router


# ---------------------------------------------------------------------------
# Lifespan — runs setup on startup and teardown on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Code before 'yield' runs at startup; code after 'yield' runs at shutdown.
    """
    # Initialise the SQLite database — creates fitgenie.db and all tables
    # if they do not already exist. Safe to call on every restart.
    init_db()
    yield
    # (shutdown cleanup goes here in future stages if needed)


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FitGenie AI — Personalized fitness and nutrition planning "
        "powered by Google Gemini."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the React frontend (localhost:3000) to call this API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
# Health check (Stage 1)
app.include_router(health_router, prefix="/api")

# Session management (Stage 2)
app.include_router(sessions_router, prefix="/api")

# Gemini diagnostics and testing (Stage 3)
app.include_router(gemini_router, prefix="/api")

# Plan generation workflow (Stage 4)
app.include_router(plans_router, prefix="/api")

# Real-time AI Coach chat (Stage 7)
app.include_router(coach_router, prefix="/api")

# Legacy LLM routes (backward compatibility)
app.include_router(bedrock_router, prefix="/api")

# Future routes will be added here in later stages:
# app.include_router(substitutions_router,  prefix="/api")

# ---------------------------------------------------------------------------
# Root redirect — useful during development
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root():
    """Root endpoint — confirms the API is reachable."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API.",
        "docs": "/docs",
        "health": "/api/health",
        "sessions": "/api/sessions",
    }
