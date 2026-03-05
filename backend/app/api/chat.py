"""
Chat endpoints — HTTP chat and WebSocket support.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.utils.database import get_db, Session, Message
from app.ai.orchestrator import generate_response

router = APIRouter()


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    escalated: bool
    language: str
    session_id: str


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    """Send a chat message and get AI response."""
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == request.session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "ended":
        raise HTTPException(status_code=400, detail="Session has ended")

    # Get conversation history
    history_result = await db.execute(
        select(Message).where(Message.session_id == request.session_id).order_by(Message.timestamp)
    )
    history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]

    # Save user message
    user_msg = Message(
        session_id=request.session_id,
        role="user",
        content=request.message,
        language=session.language
    )
    db.add(user_msg)

    # Generate AI response
    ai_result = await generate_response(
        message=request.message,
        session_id=request.session_id,
        language=session.language,
        history=history,
        tenant_name=session.tenant_id
    )

    # Save AI response
    ai_msg = Message(
        session_id=request.session_id,
        role="assistant",
        content=ai_result["reply"],
        confidence=ai_result["confidence"],
        intent=ai_result["intent"],
        language=ai_result["language"]
    )
    db.add(ai_msg)

    # Update session if escalated
    if ai_result["escalate"]:
        session.escalated = True
        session.status = "escalated"

    if ai_result["language"] != session.language:
        session.language = ai_result["language"]

    return ChatMessageResponse(
        reply=ai_result["reply"],
        intent=ai_result["intent"],
        confidence=ai_result["confidence"],
        escalated=ai_result["escalate"],
        language=ai_result["language"],
        session_id=request.session_id
    )