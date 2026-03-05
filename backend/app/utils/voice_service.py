"""
Voice Service — Speech-to-Text and Text-to-Speech
"""
import os
import base64
from typing import Optional
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv("../.env")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)


async def transcribe_audio(audio_data: bytes, language: str = "en") -> dict:
    """Convert audio to text using Deepgram."""
    try:
        lang_map = {"en": "en-US", "de": "de", "ar": "ar", "fr": "fr", "es": "es"}
        deepgram_lang = lang_map.get(language, "en-US")
        
        options = {"model": "nova-2", "language": deepgram_lang, "smart_format": True, "punctuate": True}
        payload = {"buffer": audio_data}
        
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        if response.results and response.results.channels:
            channel = response.results.channels[0]
            if channel.alternatives:
                alternative = channel.alternatives[0]
                return {
                    "text": alternative.transcript,
                    "confidence": alternative.confidence,
                    "language": language,
                    "duration": response.metadata.duration if response.metadata else 0
                }
        
        return {"text": "", "confidence": 0.0, "language": language, "error": "No transcription"}
    
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return {"text": "", "confidence": 0.0, "language": language, "error": str(e)}


async def synthesize_speech(text: str, language: str = "en", voice_name: Optional[str] = None) -> bytes:
    """Convert text to speech using Deepgram TTS."""
    try:
        default_voices = {"en": "aura-asteria-en", "de": "aura-arcas-de", "ar": "aura-arcas-ar", "fr": "aura-arcas-fr", "es": "aura-arcas-es"}
        voice = voice_name or default_voices.get(language, default_voices["en"])
        options = {"model": voice}
        
        response = deepgram.speak.rest.v("1").stream({"text": text}, options)
        
        audio_data = b""
        for chunk in response.iter_content():
            audio_data += chunk
        
        print(f"🔊 Synthesized {len(audio_data)} bytes")
        return audio_data
    
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return b""


async def synthesize_speech_base64(text: str, language: str = "en", voice_name: Optional[str] = None) -> str:
    """Return base64-encoded audio."""
    audio_bytes = await synthesize_speech(text, language, voice_name)
    return base64.b64encode(audio_bytes).decode('utf-8')


def get_supported_voices() -> dict:
    """Return available voices."""
    return {
        "en": {"aura-asteria-en": "Female, professional", "aura-luna-en": "Female, friendly", "aura-orion-en": "Male, professional", "aura-arcas-en": "Male, friendly"},
        "de": {"aura-arcas-de": "Male, German"},
        "ar": {"aura-arcas-ar": "Male, Arabic"},
        "fr": {"aura-arcas-fr": "Male, French"},
        "es": {"aura-arcas-es": "Male, Spanish"}
    }


async def simulate_voice_call(customer_audio: bytes, language: str = "en", session_id: str = "test") -> dict:
    """Simulate full voice interaction."""
    from app.ai.orchestrator import generate_response
    
    print(f"🎤 Transcribing...")
    transcription = await transcribe_audio(customer_audio, language)
    
    if not transcription.get("text"):
        return {"error": "Could not transcribe", "transcription": transcription}
    
    customer_text = transcription["text"]
    print(f"📝 Customer: {customer_text}")
    
    print(f"🤖 Generating AI response...")
    ai_result = await generate_response(message=customer_text, session_id=session_id, language=language, history=[], tenant_name="demo-shop")
    
    ai_text = ai_result["reply"]
    print(f"💬 AI: {ai_text}")
    
    print(f"🔊 Synthesizing...")
    response_audio = await synthesize_speech(ai_text, language)
    
    return {
        "transcription": {"text": customer_text, "confidence": transcription.get("confidence", 0)},
        "ai_response": {"text": ai_text, "intent": ai_result.get("intent"), "confidence": ai_result.get("confidence"), "escalate": ai_result.get("escalate")},
        "response_audio": base64.b64encode(response_audio).decode('utf-8'),
        "audio_size": len(response_audio)
    }


async def test_tts():
    """Test TTS."""
    text = "Hello! This is a test."
    audio = await synthesize_speech(text, language="en")
    return {"status": "success" if len(audio) > 0 else "failed", "audio_size": len(audio), "message": "TTS working!" if len(audio) > 0 else "TTS failed"}