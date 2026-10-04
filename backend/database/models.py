"""
models.py — SQLAlchemy ORM models (table definitions) for FitGenie AI.

Tables:
  - user_sessions  : stores the user profile collected from the form/NL input
  - plans          : stores generated 7-day plans linked to a session

Relationship:
  One user_session → many plans  (one-to-many)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database.db import Base


def _now_utc() -> datetime:
    """Return the current UTC datetime (used as column default)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Generate a new UUID4 string (used as primary key default)."""
    return str(uuid.uuid4())


# ── UserSession ────────────────────────────────────────────────────────────

class UserSession(Base):
    """
    Represents one user's profile/session.

    A session is created when the user submits their profile.
    All subsequently generated plans are linked to this session via session_id.
    """

    __tablename__ = "user_sessions"

    # Primary key — UUID string
    id = Column(String(36), primary_key=True, default=_new_uuid)

    # ── Profile fields (all nullable — collected progressively) ──────────
    age            = Column(Integer,  nullable=True,  comment="Age in years")
    gender         = Column(String(20), nullable=True, comment="e.g. Male, Female, Other")
    height         = Column(Float,    nullable=True,  comment="Height in centimetres")
    weight         = Column(Float,    nullable=True,  comment="Weight in kilograms")
    fitness_goal   = Column(String(100), nullable=True,
                            comment="e.g. Lose weight, Build muscle, Improve endurance")
    fitness_level  = Column(String(50),  nullable=True,
                            comment="e.g. Beginner, Intermediate, Advanced")
    available_time = Column(Integer,  nullable=True,
                            comment="Minutes available per day for exercise")
    equipment      = Column(Text,     nullable=True,
                            comment="Comma-separated list: e.g. Dumbbells, Resistance bands")
    food_preference = Column(String(100), nullable=True,
                             comment="e.g. Vegetarian, Vegan, No preference")
    food_restrictions = Column(Text,  nullable=True,
                               comment="Allergies or foods to avoid")
    budget         = Column(Float,    nullable=True,
                            comment="Optional weekly meal budget in local currency")

    # ── Metadata ─────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=_now_utc, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────
    # cascade="all, delete-orphan" means if a session is deleted,
    # all its associated plans are automatically deleted too.
    plans = relationship(
        "Plan",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Plan.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<UserSession id={self.id!r} goal={self.fitness_goal!r} "
            f"created_at={self.created_at}>"
        )


# ── Plan ───────────────────────────────────────────────────────────────────

class Plan(Base):
    """
    Represents a generated 7-day fitness and nutrition plan.

    The plan content is stored as a JSON string in the plan_content column.
    Multiple plans can be linked to the same session (e.g., after modifications).
    """

    __tablename__ = "plans"

    # Primary key — UUID string
    id = Column(String(36), primary_key=True, default=_new_uuid)

    # Foreign key → user_sessions.id
    session_id = Column(
        String(36),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The full 7-day plan stored as a JSON string
    plan_content = Column(Text, nullable=False,
                          comment="JSON string of the complete 7-day plan")

    # ── Metadata ─────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=_now_utc, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────
    session = relationship("UserSession", back_populates="plans")

    def __repr__(self) -> str:
        return (
            f"<Plan id={self.id!r} session_id={self.session_id!r} "
            f"created_at={self.created_at}>"
        )
