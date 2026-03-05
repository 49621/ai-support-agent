"""
Voice API Endpoints

Handles:
- Audio file upload and transcription (STT)
- Text-to-speech generation (TTS)
- Voice call simulation
- Voice configuration
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional
import base64

from app.utils.voice_service import (
    transcribe_audio,
    synthesize_speech,
    synthesize_speech_base64,
    get_supported_voices,
    simulate_voice_call
)

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio_base64: str  # Audio file encoded as base64
    language: str = "en"


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    voice_name: Optional[str] = None


class VoiceCallRequest(BaseModel):
    audio_base64: str
    session_id: str
    language: str = "en"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(...),
    language: str = "en"
):
    """
    Upload an audio file and get the transcription.
    
    Supports: mp3, wav, webm, m4a, ogg
    """
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Transcribe
        result = await transcribe_audio(audio_data, language)
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "filename": file.filename,
            "transcription": result["text"],
            "confidence": result["confidence"],
            "language": result["language"],
            "duration": result.get("duration", 0)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe-base64")
async def transcribe_base64(request: TranscribeRequest):
    """
    Send audio as base64 string and get transcription.
    Useful for frontend JavaScript applications.
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)
        
        # Transcribe
        result = await transcribe_audio(audio_data, request.language)
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "transcription": result["text"],
            "confidence": result["confidence"],
            "language": result["language"],
            "duration": result.get("duration", 0)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_endpoint(request: TTSRequest):
    """
    Convert text to speech and return as base64 audio.
    """
    try:
        # Generate speech
        audio_base64 = await synthesize_speech_base64(
            text=request.text,
            language=request.language,
            voice_name=request.voice_name
        )
        
        return {
            "audio_base64": audio_base64,
            "text": request.text,
            "language": request.language,
            "voice": request.voice_name or "default",
            "format": "mp3"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/call-simulate")
async def simulate_call(request: VoiceCallRequest):
    """
    Simulate a full voice call:
    1. Customer audio → transcription
    2. AI generates response
    3. Response → speech audio
    
    Returns both text and audio response.
    """
    try:
        # Decode audio
        audio_data = base64.b64decode(request.audio_base64)
        
        # Run simulation
        result = await simulate_voice_call(
            customer_audio=audio_data,
            language=request.language,
            session_id=request.session_id
        )
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def list_voices():
    """
    Get list of available voices per language.
    """
    return {
        "voices": get_supported_voices(),
        "message": "Available TTS voices by language"
    }


@router.get("/test/stt")
async def test_stt():
    """Test speech-to-text is working."""
    return {
        "status": "ready",
        "message": "Upload an audio file to /api/voice/transcribe to test STT",
        "supported_formats": ["mp3", "wav", "webm", "m4a", "ogg"],
        "supported_languages": ["en", "de", "ar", "fr", "es"]
    }


@router.get("/test/tts")
async def test_tts():
    """Test text-to-speech is working."""
    from app.utils.voice_service import test_tts
    result = await test_tts()
    return result