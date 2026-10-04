"""
health.py — Health check route for FitGenie AI backend.
Returns a simple JSON response to confirm the server is running.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint.
    Returns a 200 OK with a status message if the backend is running.
    """
    return {
        "status": "ok",
        "message": "FitGenie AI backend is running.",
        "version": "1.0.0"
    }
