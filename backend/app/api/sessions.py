"""
Session endpoints — create, retrieve, and end customer conversations.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.utils.database import get_db, Session, Tenant, Message

router = APIRouter()


class StartSessionRequest(BaseModel):
    tenant_id: str
    channel: str = "chat"
    language: str = "en"


class SessionResponse(BaseModel):
    session_id: str
    tenant_id: str
    channel: str
    language: str
    status: str
    started_at: str
    message: str


@router.post("/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    """Start a new customer session."""
    # Check tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == request.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        tenant = Tenant(id=request.tenant_id, name=f"Business: {request.tenant_id}", language=request.language)
        db.add(tenant)

    # Create session
    session_id = str(uuid.uuid4())
    session = Session(
        id=session_id,
        tenant_id=request.tenant_id,
        channel=request.channel,
        language=request.language,
        status="active"
    )
    db.add(session)

    # Welcome message
    welcome_messages = {
        "en": "Hello! How can I help you today?",
        "de": "Hallo! Wie kann ich Ihnen heute helfen?",
        "ar": "مرحباً! كيف يمكنني مساعدتك اليوم؟"
    }
    welcome = welcome_messages.get(request.language, welcome_messages["en"])

    msg = Message(
        session_id=session_id,
        role="assistant",
        content=welcome,
        confidence=1.0,
        intent="greeting"
    )
    db.add(msg)

    print(f"📌 New session: {session_id[:8]} | tenant: {request.tenant_id}")

    return SessionResponse(
        session_id=session_id,
        tenant_id=request.tenant_id,
        channel=request.channel,
        language=request.language,
        status="active",
        started_at=datetime.utcnow().isoformat(),
        message=welcome
    )


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get session details."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "tenant_id": session.tenant_id,
        "channel": session.channel,
        "language": session.language,
        "status": session.status,
        "escalated": session.escalated,
        "started_at": session.started_at.isoformat()
    }