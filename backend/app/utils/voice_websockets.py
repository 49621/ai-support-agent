"""
WebSocket Voice Manager — Real-Time Voice Streaming

Handles:
- Real-time audio streaming over WebSocket
- Bidirectional voice communication
- Live transcription and synthesis
- Session state management during calls
"""
import asyncio
import json
import base64
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.utils.voice_service import transcribe_audio, synthesize_speech
from app.ai.orchestrator import generate_response


class VoiceConnectionManager:
    """Manages active voice WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, dict] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new voice connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "status": "active",
            "language": "en",
            "messages_count": 0
        }
        print(f"🔌 Voice connection established: {session_id[:8]}")
    
    def disconnect(self, session_id: str):
        """Remove a voice connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        print(f"🔌 Voice connection closed: {session_id[:8]}")
    
    async def send_audio(self, session_id: str, audio_base64: str):
        """Send audio response back to client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json({
                "type": "audio_response",
                "audio": audio_base64,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def send_transcription(self, session_id: str, text: str, confidence: float):
        """Send transcription result to client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json({
                "type": "transcription",
                "text": text,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def send_status(self, session_id: str, status: str, message: str):
        """Send status update to client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json({
                "type": "status",
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def send_error(self, session_id: str, error: str):
        """Send error message to client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json({
                "type": "error",
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def get_session_state(self, session_id: str) -> Optional[dict]:
        """Get current state of a voice session."""
        return self.session_states.get(session_id)


# Global connection manager
voice_manager = VoiceConnectionManager()


async def handle_voice_message(
    session_id: str,
    audio_base64: str,
    language: str,
    tenant_id: str,
    conversation_history: list
):
    """
    Process a voice message through the full pipeline:
    1. Decode audio
    2. Transcribe (STT)
    3. Generate AI response
    4. Synthesize response (TTS)
    5. Send back to client
    """
    try:
        # Step 1: Decode audio
        audio_data = base64.b64decode(audio_base64)
        print(f"🎤 Processing {len(audio_data)} bytes of audio")
        
        # Step 2: Transcribe
        await voice_manager.send_status(session_id, "transcribing", "Converting speech to text...")
        
        transcription = await transcribe_audio(audio_data, language)
        
        if not transcription.get("text"):
            await voice_manager.send_error(session_id, "Could not transcribe audio")
            return
        
        customer_text = transcription["text"]
        confidence = transcription.get("confidence", 0.0)
        
        print(f"📝 Transcribed: {customer_text} (confidence: {confidence:.2f})")
        
        # Send transcription to client
        await voice_manager.send_transcription(session_id, customer_text, confidence)
        
        # Step 3: Generate AI response
        await voice_manager.send_status(session_id, "thinking", "AI is processing your message...")
        
        ai_result = await generate_response(
            message=customer_text,
            session_id=session_id,
            language=language,
            history=conversation_history,
            tenant_name=tenant_id
        )
        
        ai_text = ai_result["reply"]
        print(f"💬 AI response: {ai_text}")
        
        # Step 4: Synthesize speech
        await voice_manager.send_status(session_id, "synthesizing", "Converting response to speech...")
        
        response_audio = await synthesize_speech(ai_text, language)
        response_audio_base64 = base64.b64encode(response_audio).decode('utf-8')
        
        print(f"🔊 Synthesized {len(response_audio)} bytes of audio")
        
        # Step 5: Send audio response
        await voice_manager.send_audio(session_id, response_audio_base64)
        
        # Update session state
        state = voice_manager.get_session_state(session_id)
        if state:
            state["messages_count"] += 1
            state["last_message"] = customer_text
            state["last_response"] = ai_text
        
        return {
            "transcription": customer_text,
            "ai_response": ai_text,
            "intent": ai_result.get("intent"),
            "confidence": ai_result.get("confidence"),
            "escalated": ai_result.get("escalate")
        }
    
    except Exception as e:
        print(f"❌ Error processing voice message: {e}")
        await voice_manager.send_error(session_id, str(e))
        return None


async def voice_websocket_handler(
    websocket: WebSocket,
    session_id: str,
    tenant_id: str = "demo-shop",
    language: str = "en"
):
    """
    Main WebSocket handler for real-time voice communication.
    
    Client sends:
    {
        "type": "audio_chunk",
        "audio": "base64_encoded_audio",
        "language": "en"
    }
    
    Server responds with:
    {
        "type": "transcription" | "audio_response" | "status" | "error",
        ...
    }
    """
    await voice_manager.connect(session_id, websocket)
    conversation_history = []
    
    try:
        # Send welcome message
        await voice_manager.send_status(
            session_id,
            "connected",
            "Voice connection established. Start speaking!"
        )
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "audio_chunk":
                # Process audio chunk
                audio_base64 = message.get("audio")
                msg_language = message.get("language", language)
                
                if not audio_base64:
                    await voice_manager.send_error(session_id, "No audio data provided")
                    continue
                
                # Process the voice message
                result = await handle_voice_message(
                    session_id=session_id,
                    audio_base64=audio_base64,
                    language=msg_language,
                    tenant_id=tenant_id,
                    conversation_history=conversation_history
                )
                
                if result:
                    # Update conversation history
                    conversation_history.append({
                        "role": "user",
                        "content": result["transcription"]
                    })
                    conversation_history.append({
                        "role": "assistant",
                        "content": result["ai_response"]
                    })
                    
                    # Keep only last 10 messages for context
                    if len(conversation_history) > 10:
                        conversation_history = conversation_history[-10:]
            
            elif msg_type == "ping":
                # Keepalive ping
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "change_language":
                # Change language mid-call
                new_language = message.get("language", "en")
                language = new_language
                await voice_manager.send_status(
                    session_id,
                    "language_changed",
                    f"Language changed to {new_language}"
                )
            
            elif msg_type == "end_call":
                # Client is ending the call
                await voice_manager.send_status(session_id, "ending", "Call ending...")
                break
            
            else:
                await voice_manager.send_error(session_id, f"Unknown message type: {msg_type}")
    
    except WebSocketDisconnect:
        print(f"🔌 Client disconnected: {session_id[:8]}")
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await voice_manager.send_error(session_id, str(e))
    
    finally:
        voice_manager.disconnect(session_id)