"""
AI Orchestrator — The brain of the support agent.

This is where:
- Gemini processes the customer message
- Intent is detected
- Business rules are applied
- Escalation is decided
- Confidence is scored
- Multilingual responses are generated
"""
import os
from google import genai
from dotenv import load_dotenv
from app.knowledge.kb_manager import search_knowledge

load_dotenv("../.env")

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-1.5-flash"  # fast and free


# ── Intent Categories ─────────────────────────────────────────────────────────

INTENTS = [
    "order_status",        # "Where is my order?"
    "booking",             # "I want to book / cancel"
    "product_question",    # "Does this come in blue?"
    "complaint",           # "I'm unhappy with..."
    "refund_request",      # "I want a refund"
    "faq",                 # "What are your hours?"
    "troubleshooting",     # "It's not working"
    "escalation_request",  # "Let me speak to a human"
    "greeting",            # "Hello"
    "goodbye",             # "Thanks, bye"
    "out_of_scope",        # Anything outside support
    "unclear",             # Can't determine intent
]


# ── Business Rules (Hard Rules — AI cannot override these) ────────────────────

BUSINESS_RULES = """
HARD RULES — You MUST follow these exactly, no exceptions:

1. REFUNDS: Only eligible within 30 days of purchase with receipt. Never promise refunds outside this.
2. ORDER MODIFICATION: Orders can only be modified within 1 hour of placement.
3. ESCALATION: You MUST escalate to a human if:
   - Customer asks for a human agent directly
   - You are asked the same question 3 times
   - The issue involves legal threats or complaints
   - Confidence in your answer is low
   - Topic is outside your knowledge
4. PRIVACY: Never ask for full credit card numbers or passwords.
5. SCOPE: Only answer questions related to customer support. Politely decline anything else.
6. HONESTY: If you don't know, say so. Never guess or make up information.
"""


# ── Language Detection ────────────────────────────────────────────────────────

async def detect_language(text: str) -> str:
    """Detect the language of the customer's message."""
    prompt = f"""Detect the language of this text and reply with ONLY the 2-letter code.
Examples: en, de, ar, fr, es
Text: "{text}"
Reply with only the 2-letter code, nothing else."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    lang = response.text.strip().lower()[:2]
    return lang if lang in ["en", "de", "ar", "fr", "es"] else "en"


# ── Intent Detection ──────────────────────────────────────────────────────────

async def detect_intent(message: str) -> str:
    """Detect what the customer is trying to do."""
    intents_list = "\n".join(f"- {i}" for i in INTENTS)
    prompt = f"""You are an intent classifier for a customer support system.
Classify this message into ONE of these intents:
{intents_list}

Customer message: "{message}"

Reply with ONLY the intent name, nothing else."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    intent = response.text.strip().lower().replace(" ", "_")
    return intent if intent in INTENTS else "unclear"


# ── Confidence Scoring ────────────────────────────────────────────────────────

async def score_confidence(question: str, answer: str) -> float:
    """Score how confident the AI is in its answer (0.0 to 1.0)."""
    prompt = f"""Rate your confidence in this answer on a scale of 0.0 to 1.0.
0.0 = completely unsure / made up
0.5 = somewhat sure
1.0 = completely certain

Question: "{question}"
Answer: "{answer}"

Reply with ONLY a number between 0.0 and 1.0, nothing else."""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return float(response.text.strip())
    except:
        return 0.5  # default to medium confidence


# ── Should Escalate? ──────────────────────────────────────────────────────────

def should_escalate(intent: str, confidence: float, message: str) -> tuple[bool, str]:
    """
    Decide if this should be escalated to a human agent.
    Returns (should_escalate: bool, reason: str)
    """
    # Hard rule: customer explicitly asks for human
    escalation_phrases = [
        "human", "agent", "person", "representative", "manager",
        "speak to someone", "real person", "mensch", "mitarbeiter",  # German
        "إنسان", "موظف"  # Arabic
    ]
    message_lower = message.lower()
    if any(phrase in message_lower for phrase in escalation_phrases):
        return True, "Customer requested human agent"

    # Hard rule: explicit escalation intent
    if intent == "escalation_request":
        return True, "Escalation requested"

    # Hard rule: low confidence
    if confidence < float(os.getenv("CONFIDENCE_THRESHOLD", "0.7")):
        return True, f"Low confidence: {confidence:.2f}"

    # Hard rule: legal/complaint escalation
    legal_phrases = ["lawyer", "sue", "legal", "court", "rechtsanwalt", "klage"]
    if any(phrase in message_lower for phrase in legal_phrases):
        return True, "Legal threat detected"

    return False, ""


# ── Main AI Response Generator ────────────────────────────────────────────────

async def generate_response(
    message: str,
    session_id: str,
    language: str,
    history: list,
    tenant_name: str = "our company",
    knowledge_context: str = ""
) -> dict:
    """
    Main function — takes a customer message and returns a full AI response.

    Returns:
        {
            "reply": str,          # the response text
            "intent": str,         # detected intent
            "confidence": float,   # 0.0 to 1.0
            "escalate": bool,      # should we escalate?
            "escalate_reason": str,# why we're escalating
            "language": str        # language used
        }
    """

    # Step 1: Detect language (use detected or provided)
    detected_lang = await detect_language(message)
    # Use detected language if different from session language
    response_language = detected_lang

    # Step 2: Detect intent
    intent = await detect_intent(message)

    # Step 2.5: Retrieve from knowledge base if not provided
    if not knowledge_context:
        try:
            knowledge_results = search_knowledge(tenant_name, message, top_k=3)
            if knowledge_results:
                knowledge_context = "\n\n".join([
                    f"[Relevant Info {i+1}]: {doc['content']}"
                    for i, doc in enumerate(knowledge_results)
                ])
        except Exception as e:
            print(f"⚠️ Knowledge search failed: {e}")
            knowledge_context = ""

    # Step 3: Build conversation history for context
    history_text = ""
    if history:
        history_text = "\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-6:]  # last 6 messages for context
        ])

    # Step 4: Build knowledge context
    knowledge_section = ""
    if knowledge_context:
        knowledge_section = f"""
KNOWLEDGE BASE (use this to answer accurately):
{knowledge_context}
"""

    # Step 5: Language instruction
    language_instructions = {
        "en": "Respond in English.",
        "de": "Antworte auf Deutsch.",
        "ar": "أجب باللغة العربية.",
        "fr": "Répondez en français.",
        "es": "Responde en español."
    }
    lang_instruction = language_instructions.get(
        response_language,
        "Respond in the same language as the customer."
    )

    # Step 6: Build the full system prompt
    system_prompt = f"""You are a helpful customer support agent for {tenant_name}.

{BUSINESS_RULES}

{knowledge_section}

CONVERSATION STYLE:
- Be friendly, professional, and concise
- Keep responses under 3 sentences when possible
- Ask one clarifying question at a time if needed
- Never make up information you don't have
- {lang_instruction}

DETECTED INTENT: {intent}

CONVERSATION HISTORY:
{history_text}
"""

    # Step 7: Generate the response
    full_prompt = f"{system_prompt}\n\nCUSTOMER: {message}\n\nASSISTANT:"

    response = client.models.generate_content(
        model=MODEL,
        contents=full_prompt
    )
    reply = response.text.strip()

    # Step 8: Score confidence
    confidence = await score_confidence(message, reply)

    # Step 9: Check escalation
    escalate, escalate_reason = should_escalate(intent, confidence, message)

    # Step 10: If escalating, add a human handoff message
    if escalate:
        handoff_messages = {
            "en": "\n\nI'm connecting you with a human agent now. Please hold on.",
            "de": "\n\nIch verbinde Sie jetzt mit einem menschlichen Mitarbeiter.",
            "ar": "\n\nسأقوم بتحويلك إلى موظف الآن. يرجى الانتظار."
        }
        reply += handoff_messages.get(response_language, handoff_messages["en"])

    print(f"🤖 [{session_id[:8]}] Intent: {intent} | Confidence: {confidence:.2f} | Escalate: {escalate}")

    return {
        "reply": reply,
        "intent": intent,
        "confidence": confidence,
        "escalate": escalate,
        "escalate_reason": escalate_reason,
        "language": response_language
    }