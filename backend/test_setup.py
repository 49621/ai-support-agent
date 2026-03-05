import os, sys
from dotenv import load_dotenv

load_dotenv("../.env")

print("Checking your environment...\n")

# 1. Python version
v = sys.version_info
print(f"✅ Python {v.major}.{v.minor} — OK")

# 2. Gemini key
gemini_key = os.getenv("GEMINI_API_KEY")
assert gemini_key, "❌ GEMINI_API_KEY missing in .env"
print("✅ Gemini API key — found")

# 3. Deepgram key
dg_key = os.getenv("DEEPGRAM_API_KEY")
assert dg_key, "❌ DEEPGRAM_API_KEY missing in .env"
print("✅ Deepgram API key — found")

# 4. FastAPI
import fastapi
print(f"✅ FastAPI {fastapi.__version__} — OK")

# 5. New Gemini SDK
from google import genai
print("✅ Gemini SDK (new) — OK")

# 6. ChromaDB
import chromadb
print(f"✅ ChromaDB {chromadb.__version__} — OK")

# 7. Deepgram
from deepgram import DeepgramClient
print("✅ Deepgram SDK — OK")

# 8. Live Gemini API call
print("\n🤖 Testing live Gemini connection...")
client = genai.Client(api_key=gemini_key)
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Reply with exactly: 'Gemini is ready!' and nothing else."
)
print(f"✅ Gemini replied: {response.text.strip()}")

print("""
╔══════════════════════════════════════╗
║  🎉 ALL CHECKS PASSED!               ║
║  You are ready for Phase 2!          ║
╚══════════════════════════════════════╝
""")