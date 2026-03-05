"""
AI Support Agent - Streamlit Frontend
Beautiful chat interface with voice support
"""
import streamlit as st
import requests
import base64
from audio_recorder_streamlit import audio_recorder
import uuid

# Page config
st.set_page_config(
    page_title="AI Support Agent",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0;
    }
    
    /* Chat container */
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Title */
    h1 {
        color: white !important;
        text-align: center;
        padding: 2rem 0 1rem 0;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }
    
    /* Status badge */
    .status-badge {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        text-align: center;
        margin: 0 auto 2rem auto;
        width: fit-content;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        display: flex;
        gap: 1rem;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 2rem;
    }
    
    .chat-message.assistant {
        background: white;
        color: #1f2937;
        margin-right: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .chat-message .avatar {
        font-size: 2rem;
        flex-shrink: 0;
    }
    
    .chat-message .content {
        flex: 1;
    }
    
    /* Input area */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
    }
    
    /* Language selector */
    .stRadio > div {
        display: flex;
        gap: 0.5rem;
        justify-content: center;
        flex-wrap: wrap;
    }
    
    .stRadio > div > label {
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .stRadio > div > label:hover {
        background: #f3f4f6;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "http://localhost:8000/api"

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Functions
def start_session(language='en'):
    """Start a new chat session"""
    try:
        response = requests.post(
            f"{API_URL}/sessions/start",
            json={
                "tenant_id": "demo-shop",
                "channel": "chat",
                "language": language
            }
        )
        data = response.json()
        st.session_state.session_id = data['session_id']
        st.session_state.messages = [{
            'role': 'assistant',
            'content': data['message']
        }]
        return True
    except Exception as e:
        st.error(f"Failed to start session: {e}")
        return False

def send_message(message):
    """Send a message to the AI"""
    if not st.session_state.session_id:
        st.error("No active session. Please refresh the page.")
        return
    
    try:
        response = requests.post(
            f"{API_URL}/chat/message",
            json={
                "session_id": st.session_state.session_id,
                "message": message
            }
        )
        data = response.json()
        return data['reply']
    except Exception as e:
        return f"Error: {str(e)}"

def transcribe_audio(audio_bytes, language='en'):
    """Transcribe audio to text"""
    try:
        files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
        response = requests.post(
            f"{API_URL}/voice/transcribe",
            files=files,
            params={'language': language}
        )
        data = response.json()
        return data.get('transcription', '')
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        return None

# UI
st.markdown("<h1>🤖 AI Support Agent</h1>", unsafe_allow_html=True)

# Language selector
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    language = st.radio(
        "Language",
        ['en', 'de', 'ar', 'fr', 'es'],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )
    if language != st.session_state.language:
        st.session_state.language = language
        if st.session_state.session_id:
            st.info("Language changed. Starting new session...")
            start_session(language)
            st.rerun()

# Start session if not exists
if not st.session_state.session_id:
    start_session(st.session_state.language)

# Status badge
language_names = {
    'en': '🇬🇧 English',
    'de': '🇩🇪 Deutsch',
    'ar': '🇸🇦 العربية',
    'fr': '🇫🇷 Français',
    'es': '🇪🇸 Español'
}
st.markdown(
    f"<div class='status-badge'>✅ Connected · {language_names.get(st.session_state.language, 'EN')}</div>",
    unsafe_allow_html=True
)

# Chat container
st.markdown("---")

# Display chat messages
for message in st.session_state.messages:
    role = message['role']
    content = message['content']
    
    if role == 'user':
        st.markdown(
            f"""
            <div class="chat-message user">
                <div class="avatar">👤</div>
                <div class="content">{content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="chat-message assistant">
                <div class="avatar">🤖</div>
                <div class="content">{content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Voice input
st.markdown("### 🎤 Voice Input")
audio_bytes = audio_recorder(
    text="Click to record",
    recording_color="#667eea",
    neutral_color="#e5e7eb",
    icon_size="2x"
)

if audio_bytes:
    with st.spinner("Transcribing..."):
        transcription = transcribe_audio(audio_bytes, st.session_state.language)
        if transcription:
            st.session_state.messages.append({
                'role': 'user',
                'content': transcription
            })
            
            with st.spinner("AI is thinking..."):
                reply = send_message(transcription)
                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': reply
                })
            st.rerun()

# Text input
st.markdown("### 💬 Text Input")
user_input = st.text_input(
    "Type your message...",
    key="user_input",
    label_visibility="collapsed"
)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Send Message", use_container_width=True):
        if user_input:
            st.session_state.messages.append({
                'role': 'user',
                'content': user_input
            })
            
            with st.spinner("AI is thinking..."):
                reply = send_message(user_input)
                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': reply
                })
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: rgba(255,255,255,0.6); font-size: 0.8rem;'>Powered by Gemini AI · Deepgram Voice</div>",
    unsafe_allow_html=True
)