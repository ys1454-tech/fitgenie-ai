"""
crud.py — Database CRUD operations for FitGenie AI.

Provides simple, reusable functions for creating and reading
user sessions and generated plans.

All functions accept a SQLAlchemy Session object, which is injected
by FastAPI's dependency system via get_db() in db.py.

Note: "Session" here refers to a SQLAlchemy database session,
NOT a user session. The user session model is called UserSession.
"""

import json
import uuid

from sqlalchemy.orm import Session

from database.models import Plan, UserSession


# ── UserSession CRUD ───────────────────────────────────────────────────────

def create_user_session(db: Session, profile: dict) -> UserSession:
    """
    Create and persist a new user session with the given profile data.

    Args:
        db      : SQLAlchemy database session
        profile : Dict of profile fields (age, gender, height, etc.)
                  Unknown keys are silently ignored.

    Returns:
        The newly created UserSession ORM object.
    """
    # Only pass fields that exist on the model to avoid unexpected kwargs
    allowed_fields = {
        "age", "gender", "height", "weight", "fitness_goal",
        "fitness_level", "available_time", "equipment",
        "food_preference", "food_restrictions", "budget",
    }
    filtered = {k: v for k, v in profile.items() if k in allowed_fields}

    session = UserSession(id=str(uuid.uuid4()), **filtered)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_session(db: Session, session_id: str) -> UserSession | None:
    """
    Retrieve a user session by its ID.

    Returns None if no session with the given ID exists.
    """
    return db.query(UserSession).filter(UserSession.id == session_id).first()


def list_user_sessions(db: Session, limit: int = 20) -> list[UserSession]:
    """
    Return the most recent user sessions (newest first).
    Mainly useful for admin/debug purposes.
    """
    return (
        db.query(UserSession)
        .order_by(UserSession.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Plan CRUD ──────────────────────────────────────────────────────────────

def save_plan(db: Session, session_id: str, plan_data: dict | str) -> Plan:
    """
    Save a generated plan linked to an existing user session.

    Args:
        db         : SQLAlchemy database session
        session_id : ID of the UserSession this plan belongs to
        plan_data  : The plan as a Python dict (will be JSON-serialised)
                     or as a raw JSON string.

    Returns:
        The newly created Plan ORM object.

    Raises:
        ValueError if no UserSession with the given session_id exists.
    """
    # Ensure the parent session exists
    session = get_user_session(db, session_id)
    if session is None:
        raise ValueError(f"UserSession '{session_id}' not found.")

    # Serialise to JSON string if a dict was passed
    if isinstance(plan_data, dict):
        content = json.dumps(plan_data, ensure_ascii=False)
    else:
        content = plan_data  # assume already a JSON string

    plan = Plan(
        id=str(uuid.uuid4()),
        session_id=session_id,
        plan_content=content,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_latest_plan(db: Session, session_id: str) -> Plan | None:
    """
    Return the most recently created plan for a given session.

    Returns None if the session has no plans yet.
    """
    return (
        db.query(Plan)
        .filter(Plan.session_id == session_id)
        .order_by(Plan.created_at.desc())
        .first()
    )


def get_all_plans(db: Session, session_id: str) -> list[Plan]:
    """
    Return all plans for a given session, newest first.
    """
    return (
        db.query(Plan)
        .filter(Plan.session_id == session_id)
        .order_by(Plan.created_at.desc())
        .all()
    )


def get_plan_by_id(db: Session, plan_id: str) -> Plan | None:
    """
    Return a single plan by its ID.

    Returns None if not found.
    """
    return db.query(Plan).filter(Plan.id == plan_id).first()
