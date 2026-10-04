"""
sessions.py — API routes for user session management.

Endpoints:
  POST /api/sessions                    — Create a new user session
  GET  /api/sessions/{session_id}       — Get session details
  GET  /api/sessions/{session_id}/plan  — Get the latest plan for a session
  GET  /api/sessions/{session_id}/plans — Get all plans for a session
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.crud import (
    create_user_session,
    get_all_plans,
    get_latest_plan,
    get_user_session,
)
from database.db import get_db

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ── Request / Response schemas ─────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    """
    Profile fields sent when creating a new session.
    All fields are optional at creation time — they can be
    filled in progressively as the user completes the form.
    """
    age:               int   | None = Field(None, ge=5,  le=120,  description="Age in years")
    gender:            str   | None = Field(None, max_length=20,  description="e.g. Male, Female, Other")
    height:            float | None = Field(None, gt=0,  le=300,  description="Height in cm")
    weight:            float | None = Field(None, gt=0,  le=500,  description="Weight in kg")
    fitness_goal:      str   | None = Field(None, max_length=100, description="e.g. Lose weight")
    fitness_level:     str   | None = Field(None, max_length=50,  description="e.g. Beginner")
    available_time:    int   | None = Field(None, ge=1,  le=480,  description="Minutes per day")
    equipment:         str   | None = Field(None, max_length=500, description="Comma-separated equipment list")
    food_preference:   str   | None = Field(None, max_length=100, description="e.g. Vegetarian")
    food_restrictions: str   | None = Field(None, max_length=500, description="Allergies or foods to avoid")
    budget:            float | None = Field(None, ge=0,            description="Optional weekly budget")


class SessionResponse(BaseModel):
    """Response returned after creating or fetching a session."""
    id:                str
    age:               int   | None
    gender:            str   | None
    height:            float | None
    weight:            float | None
    fitness_goal:      str   | None
    fitness_level:     str   | None
    available_time:    int   | None
    equipment:         str   | None
    food_preference:   str   | None
    food_restrictions: str   | None
    budget:            float | None
    created_at:        str
    plan:              dict  | None = None

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    """Response for a single plan."""
    id:           str
    session_id:   str
    plan_content: dict   # Deserialised from JSON string
    created_at:   str

    model_config = {"from_attributes": True}


# ── Helper ─────────────────────────────────────────────────────────────────

def _session_to_response(s) -> SessionResponse:
    plan_data = None
    if getattr(s, "plans", None) and len(s.plans) > 0:
        latest_plan = s.plans[-1]
        try:
            plan_data = json.loads(latest_plan.plan_content)
        except Exception:
            plan_data = None

    return SessionResponse(
        id=s.id,
        age=s.age,
        gender=s.gender,
        height=s.height,
        weight=s.weight,
        fitness_goal=s.fitness_goal,
        fitness_level=s.fitness_level,
        available_time=s.available_time,
        equipment=s.equipment,
        food_preference=s.food_preference,
        food_restrictions=s.food_restrictions,
        budget=s.budget,
        created_at=s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
        plan=plan_data,
    )


def _plan_to_response(p) -> PlanResponse:
    return PlanResponse(
        id=p.id,
        session_id=p.session_id,
        plan_content=json.loads(p.plan_content),
        created_at=p.created_at.isoformat(),
    )


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=SessionResponse)
def create_session(
    body: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new user session with the provided profile data.
    Returns the created session including its generated ID.
    """
    user_session = create_user_session(db, body.model_dump())
    return _session_to_response(user_session)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve a session by its ID."""
    user_session = get_user_session(db, session_id)
    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return _session_to_response(user_session)


@router.get("/{session_id}/plan", response_model=PlanResponse)
def get_latest_plan_for_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Return the most recently generated plan for a session.
    Returns 404 if the session has no plans yet.
    """
    plan = get_latest_plan(db, session_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No plans found for session '{session_id}'.",
        )
    return _plan_to_response(plan)


@router.get("/{session_id}/plans", response_model=list[PlanResponse])
def get_all_plans_for_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Return all generated plans for a session, newest first.
    Returns an empty list if none exist.
    """
    plans = get_all_plans(db, session_id)
    return [_plan_to_response(p) for p in plans]
