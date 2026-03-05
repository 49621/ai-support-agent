"""
Database setup — SQLite for development, easy to upgrade to Postgres later.
Stores: sessions, messages, tenants (businesses)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, Integer
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv("../.env")

# Database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/support_agent.db")

# Fix SQLite URL for async
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for all models
Base = declarative_base()


# ── Models ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    """A business using the support agent."""
    __tablename__ = "tenants"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    language    = Column(String, default="en")
    voice_on    = Column(Boolean, default=True)
    chat_on     = Column(Boolean, default=True)
    system_prompt = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """A single customer conversation."""
    __tablename__ = "sessions"

    id            = Column(String, primary_key=True)
    tenant_id     = Column(String, nullable=False)
    channel       = Column(String, default="chat")
    language      = Column(String, default="en")
    status        = Column(String, default="active")
    escalated     = Column(Boolean, default=False)
    resolution    = Column(String, default="pending")
    credit_used   = Column(Float, default=0.0)
    started_at    = Column(DateTime, default=datetime.utcnow)
    ended_at      = Column(DateTime, nullable=True)


class Message(Base):
    """A single message inside a session."""
    __tablename__ = "messages"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    session_id       = Column(String, nullable=False)
    role             = Column(String, nullable=False)
    content          = Column(Text, nullable=False)
    confidence       = Column(Float, default=1.0)
    intent           = Column(String, default="unknown")
    language         = Column(String, default="en")
    timestamp        = Column(DateTime, default=datetime.utcnow)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def init_db():
    """Create all tables if they don't exist."""
    import os
    os.makedirs("./data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency — provides a database session to route handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise