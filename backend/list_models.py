import os
from google import genai
from dotenv import load_dotenv

load_dotenv("../.env")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available Gemini models:\n")
for model in client.models.list():
    print(f"- {model.name}")