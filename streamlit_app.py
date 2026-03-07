"""
AI Support Agent - Streamlit Frontend
Beautiful chat interface with voice support via Gemini multimodal
"""
import streamlit as st
import base64
import uuid
from google import genai
from google.genai import types

API_KEY = "AIzaSyDPJsIAngRVKs4bQTyyD_m2WG1UQ7ah10Y"
client = genai.Client(api_key=API_KEY)

# ── Shopping context ─────────────────────────────────────────────────────────

SHOPPING_CONTEXT = """
You are a helpful shopping assistant for an online store. You have access to the following customer data:

CUSTOMER PROFILE:
- Name: Alex Johnson
- Email: alex.johnson@email.com
- Member since: January 2023

RECENT ORDERS:
1. Order #ORD-7821 (Placed: March 1, 2026)
   - Nike Air Max Sneakers (Size 10, Black) - $129.99
   - Status: Out for Delivery (Expected: March 7, 2026)
   - Tracking: DHL-4892017

2. Order #ORD-7654 (Placed: February 20, 2026)
   - Samsung 65" 4K Smart TV - $899.99
   - Status: Delivered (February 25, 2026)
   - Eligible for return until: March 27, 2026

3. Order #ORD-7502 (Placed: February 10, 2026)
   - Levi's Slim Fit Jeans (Size 32, Blue) - $69.99
   - Apple AirPods Pro - $249.99
   - Status: Delivered (February 14, 2026)
   - Eligible for exchange until: March 14, 2026 (EXPIRED)

4. Order #ORD-7301 (Placed: January 28, 2026)
   - Coffee Maker Deluxe - $89.99
   - Status: Cancelled (Refund processed on Feb 1, 2026)

STORE POLICIES:
- Returns accepted within 30 days of delivery
- Exchanges accepted within 30 days of delivery
- Cancellations only possible if order is not yet shipped
- Refunds processed within 5-7 business days
- Free shipping on orders above $50

INSTRUCTIONS:
- Be friendly, concise, and helpful
- Always reference specific order numbers and details when relevant
- If asked about cancellation, check if the order is already shipped
- Guide users through exchange/return steps clearly
- For issues you cannot resolve, ask them to contact support@store.com
- Keep responses short and to the point (2-5 sentences max unless steps are needed)
"""

# ── Gemini helpers ────────────────────────────────────────────────────────────

def get_gemini_reply(conversation_history):
    """Text-only path: send conversation history and get a reply."""
    try:
        prompt = SHOPPING_CONTEXT + "\n\nCONVERSATION HISTORY:\n"
        for msg in conversation_history:
            role = "Customer" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        prompt += "Assistant:"

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        return response.text.strip() if response.text else "Sorry, I couldn't generate a response."
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"


def get_gemini_reply_from_audio(audio_bytes, conversation_history, language_label):
    """
    Audio path: send audio directly to Gemini multimodal with the correct mime type.
    One single API call — Gemini listens to the audio and replies.
    Returns (transcription_for_display, reply_text).
    """
    try:
        # ── 1. Detect mime type from magic bytes ─────────────────────────
        if audio_bytes[:4] == b"RIFF":
            mime_type = "audio/wav"
        elif audio_bytes[:4] == b"OggS":
            mime_type = "audio/ogg"
        elif audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3") or audio_bytes[:3] == b"ID3":
            mime_type = "audio/mpeg"
        else:
            # st.audio_input records as webm/opus in Chrome & Firefox
            mime_type = "audio/webm"

        # ── 2. Base64-encode the raw audio bytes ──────────────────────────
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # ── 3. Build conversation history string ──────────────────────────
        history_str = ""
        for msg in conversation_history:
            role = "Customer" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        # ── 4. Single multimodal prompt ───────────────────────────────────
        prompt_text = (
            SHOPPING_CONTEXT
            + f"\n\nThe customer is speaking in: {language_label}\n\n"
            + "CONVERSATION HISTORY:\n"
            + history_str
            + "\nThe customer just sent a voice message (audio attached).\n"
            + "Respond in exactly two lines:\n"
            + "HEARD: <transcribe exactly what the customer said>\n"
            + "REPLY: <your helpful assistant response following the instructions above>"
        )

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt_text),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime_type,
                                data=audio_b64,
                            )
                        ),
                    ],
                )
            ],
        )

        raw = response.text.strip() if response.text else ""

        # ── 5. Parse HEARD / REPLY from response ──────────────────────────
        transcription = "[voice message]"
        reply = raw  # fallback: treat entire response as the reply

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("HEARD:"):
                transcription = stripped[6:].strip()
            elif stripped.upper().startswith("REPLY:"):
                reply = stripped[6:].strip()

        if not reply:
            reply = "I received your voice message but had trouble generating a response. Please try again."

        return transcription, reply

    except Exception as e:
        return None, f"Sorry, I encountered an error processing your voice message: {str(e)}"


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Support Agent",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp { max-width: 800px; margin: 0 auto; }

    h1 {
        color: white !important;
        text-align: center;
        padding: 2rem 0 1rem 0;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }

    .status-badge {
        background: rgba(255,255,255,0.2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        text-align: center;
        margin: 0 auto 2rem auto;
        width: fit-content;
        font-size: 0.9rem;
        font-weight: 600;
    }

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
        to   { opacity: 1; transform: translateY(0); }
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
    .chat-message .avatar { font-size: 2rem; flex-shrink: 0; }
    .chat-message .content { flex: 1; }

    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
    }

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
        box-shadow: 0 8px 16px rgba(102,126,234,0.4);
    }

    .stRadio > div { display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap; }
    .stRadio > div > label {
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .stRadio > div > label:hover { background: #f3f4f6; transform: scale(1.05); }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Hi Alex! I'm your AI shopping assistant. How can I help you today? You can ask about your orders, returns, or anything else!",
    }]
if "language" not in st.session_state:
    st.session_state.language = "en"
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

language_names = {
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "ar": "🇸🇦 العربية",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
}

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("<h1>🤖 AI Support Agent</h1>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    language = st.radio(
        "Language",
        ["en", "de", "ar", "fr", "es"],
        index=["en", "de", "ar", "fr", "es"].index(st.session_state.language),
        horizontal=True,
        label_visibility="collapsed",
    )
    if language != st.session_state.language:
        st.session_state.language = language
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Hi Alex! Language updated. How can I help you today?",
        }]
        st.rerun()

st.markdown(
    f"<div class='status-badge'>✅ Connected · {language_names.get(st.session_state.language, 'EN')}</div>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Chat history ──────────────────────────────────────────────────────────────

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    if role == "user":
        st.markdown(
            f'<div class="chat-message user"><div class="avatar">👤</div><div class="content">{content}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="chat-message assistant"><div class="avatar">🤖</div><div class="content">{content}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── Voice Input ───────────────────────────────────────────────────────────────

st.markdown("### 🎤 Voice Input")
st.caption("Record your message — Gemini will listen and respond directly.")

audio_input = st.audio_input("Record your message", key="audio_recorder", label_visibility="collapsed")

if audio_input is not None:
    # Read bytes first, then use for both playback and Gemini
    audio_bytes = audio_input.read()
    audio_id = hash(audio_bytes)

    # Play back using bytes wrapped in BytesIO
    import io
    st.audio(io.BytesIO(audio_bytes), format="audio/webm")

    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id

        with st.spinner("🎧 Gemini is listening and thinking..."):
            lang_label = language_names.get(st.session_state.language, "English")
            transcription, reply = get_gemini_reply_from_audio(
                audio_bytes,
                st.session_state.messages,
                lang_label,
            )

        st.session_state.messages.append({
            "role": "user",
            "content": f"🎤 {transcription}" if transcription else "🎤 [voice message]",
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
        })
        st.rerun()

# ── Text Input ────────────────────────────────────────────────────────────────

st.markdown("### 💬 Text Input")

with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Type your message...",
        key="user_input",
        label_visibility="collapsed",
        placeholder="e.g. What's the status of my order?",
    )
    submitted = st.form_submit_button("Send Message", use_container_width=True)

if submitted and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("AI is thinking..."):
        reply = get_gemini_reply(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:rgba(255,255,255,0.6);font-size:0.8rem;'>Powered by Gemini AI · Multimodal Audio</div>",
    unsafe_allow_html=True,
)

