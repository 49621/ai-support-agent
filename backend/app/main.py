"""
AI Support Agent — Main Application
Phase 2: Backend API Core
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, sessions, health, knowledge, voice
from app.utils.database import init_db
import uvicorn

# Create the FastAPI app
app = FastAPI(
    title="AI Support Agent",
    description="AI-powered customer support with voice and chat",
    version="1.0.0"
)

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route handlers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])


@app.on_event("startup")
async def startup():
    """Runs when server starts — sets up the database."""
    print("🚀 AI Support Agent starting up...")
    await init_db()
    print("✅ Database ready")
    print("✅ Server is live at http://localhost:8000")
    print("✅ API docs at http://localhost:8000/docs")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)