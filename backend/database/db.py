"""
db.py — SQLite database connection setup for FitGenie AI.

Responsibilities:
  - Create the SQLAlchemy engine pointing at fitgenie.db
  - Provide a session factory (SessionLocal) for database operations
  - Provide the shared declarative Base that all ORM models inherit from
  - Expose get_db() for FastAPI dependency injection
  - Expose init_db() called once at application startup to create tables
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Database file path ─────────────────────────────────────────────────────
# Place fitgenie.db in the backend/ folder next to main.py.
# The path is relative to wherever uvicorn is launched from.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'fitgenie.db')}"

# ── Engine ─────────────────────────────────────────────────────────────────
# check_same_thread=False is required for SQLite when used with FastAPI,
# because FastAPI handles requests in multiple threads.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set True to log all SQL statements during development
)

# ── Session factory ────────────────────────────────────────────────────────
# Each request gets its own database session, opened and closed cleanly.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Declarative base ───────────────────────────────────────────────────────
# All ORM model classes in models.py inherit from this Base.
class Base(DeclarativeBase):
    pass


# ── Dependency injection helper ────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session per request.
    Guarantees the session is always closed after the request completes,
    even if an exception is raised.

    Usage in a route:
        from database.db import get_db
        from sqlalchemy.orm import Session

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Database initialisation ────────────────────────────────────────────────
def init_db() -> None:
    """
    Create all database tables defined by ORM models if they do not yet exist.
    Called once at application startup via FastAPI's lifespan event in main.py.
    SQLite will create the .db file automatically if it does not exist.
    """
    # Import models here so SQLAlchemy registers them on Base.metadata
    # before create_all() is called.
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_database_url() -> str:
    """Return the current database URL (useful for health/info endpoints)."""
    return DATABASE_URL
