# 🤖 AI Support Agent

A full-stack AI-powered customer support system with voice capabilities, multilingual support, and RAG knowledge base.

## ✨ Features

- 💬 Real-time chat interface (Streamlit + React)
- 🎤 Voice support (Deepgram STT + TTS)
- 🌍 Multilingual (English, German, Arabic, French, Spanish)
- 📚 RAG knowledge base (ChromaDB)
- 🔄 WebSocket support for real-time communication
- 🤖 Powered by Google Gemini AI
- 📊 Session management & conversation history
- 🎨 Beautiful gradient UI

## 🏗️ Tech Stack

**Backend:**
- FastAPI
- Python 3.11
- Google Gemini API
- Deepgram (STT/TTS)
- ChromaDB (Vector DB)
- SQLite

**Frontend:**
- Streamlit (primary)
- React (alternative widget)

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- Gemini API key
- Deepgram API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR-USERNAME/ai-support-agent.git
cd ai-support-agent
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
cd ..
pip install -r requirements-streamlit.txt
```

4. Set up environment variables:
Create `.env` file in project root:
```
GEMINI_API_KEY=your_key_here
DEEPGRAM_API_KEY=your_key_here
DATABASE_URL=sqlite:///./data/support_agent.db
CHROMA_DB_PATH=./data/chroma_db
CONFIDENCE_THRESHOLD=0.7
```

### Running the Application

**Backend (Terminal 1):**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Streamlit Frontend (Terminal 2):**
```bash
streamlit run streamlit_app.py
```

Open: http://localhost:8501

## 📖 API Documentation

Once the backend is running, visit:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## 🎯 Project Structure
```
ai-support-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── ai/           # AI orchestration
│   │   ├── knowledge/    # RAG & ChromaDB
│   │   └── utils/        # Voice, database, etc.
│   └── requirements.txt
├── streamlit_app.py      # Streamlit frontend
├── chat-widget.html      # React widget
├── .env                  # Environment variables
└── README.md
```

## 🌟 Features in Detail

### Voice Support
- Real-time voice recording
- Speech-to-text transcription
- Text-to-speech responses
- Multi-language voice support

### Knowledge Base
- Upload documents (.txt files)
- Semantic search with ChromaDB
- RAG for accurate responses
- Per-tenant knowledge isolation

### AI Capabilities
- Intent detection
- Confidence scoring
- Automatic escalation to human agents
- Multilingual conversations
- Context-aware responses

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License

## 👨‍💻 Author

Built by [Your Name]

## 🙏 Acknowledgments

- Google Gemini AI
- Deepgram
- FastAPI
- Streamlit