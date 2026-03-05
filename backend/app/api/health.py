"""
Health check endpoints
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "ok",
        "message": "AI Support Agent is running",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }