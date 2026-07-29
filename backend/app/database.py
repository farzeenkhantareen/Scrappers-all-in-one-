"""
Database setup: async SQLAlchemy engine, session factory, and base model.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, String
from datetime import datetime, timezone
import uuid

from app.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Engine & Session
# ─────────────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base Model
# ─────────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Abstract base class for all ORM models."""

    def to_dict(self) -> dict:
        """Serialize model to dictionary."""
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }


# ─────────────────────────────────────────────────────────────────────────────
# Dependency: get DB session
# ─────────────────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Create all tables
# ─────────────────────────────────────────────────────────────────────────────
async def init_db():
    """Create all database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
