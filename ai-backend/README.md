# SapioCode AI Engine (The Brain) 🧠

**Role 2: The AI Engineer** - Intelligence Cluster for SapioCode Platform

## Overview
This is the AI backend service that powers the "Intelligence Cluster" of SapioCode. It handles:
- **Socratic Tutoring**: Generating hints that guide without revealing answers
- **Audio Transcription**: Converting Viva Voce audio to text (future)
- **Semantic Verification**: Validating student understanding (future)
- **AI Problem Generation**: Creating curriculum content (future)

## Current Status
✅ **Day 1 Complete**: Foundation setup with Groq AI API integration

## Setup Instructions

### 1. Get Your FREE Groq API Key
1. Go to: https://console.groq.com
2. Sign up (it's FREE!)
3. Navigate to "API Keys"
4. Create a new API key
5. Copy it for the next step

### 2. Create Virtual Environment
```bash
cd d:\sapiocode\ai-backend
python -m venv venv
```

### 2. Activate Virtual Environment
```bash
# Windows Command Prompt
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy the example file
copy .env.example .env

# Edit .env and add your Groq API key
```

Your `.env` should look like:
```env
GROQ_API_KEY=gsk_your_actual_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
```

### 5. Run the Server
```bash
uvicorn app.main:app --reload --port 8000
```

The server will start at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

## API Endpoints

### Core Endpoints
- `GET /` - Welcome message
- `GET /health` - Health check for monitoring
- `GET /api/ai/status` - Check if Groq API is configured

### AI Endpoints
- `POST /api/ai/test` - Test Groq API connection
- `POST /api/ai/hint` - Generate Socratic hint for stuck student

## Testing

Use the `test.http` file with REST Client extension in VS Code, or use curl:

```bash
# Test health
curl http://localhost:8000/health

# Test AI (replace with your problem)
curl -X POST http://localhost:8000/api/ai/hint \
  -H "Content-Type: application/json" \
  -d '{
    "problem_description": "Write a function to reverse a linked list",
    "student_code": "def reverse(head):\n    return head",
    "stuck_duration": 120
  }'
```

## Project Structure
```
ai-backend/
├── app/
│   ├── api/
│   │   └── ai_routes.py      # API endpoints
│   ├── core/
│   │   └── config.py          # Configuration settings
│   ├── services/
│   │   └── groq_service.py    # Groq API wrapper
│   ├── models/                # Pydantic models (future)
│   └── main.py                # FastAPI application
├── tests/                     # Test files (future)
├── venv/                      # Virtual environment
├── .env                       # Environment variables (not in git)
├── .env.example               # Example environment file
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Tech Stack
- **FastAPI**: Modern Python web framework
- **Groq API**: Ultra-fast LLM inference (FREE!)
- **httpx**: Async HTTP client
- **Uvicorn**: ASGI server

## Integration Points

### With Role 1 (Systems Architect)
- WebSocket events for code changes
- Docker sandbox for code execution
- Memory visualization data

### With Role 3 (Data Architect)
- Knowledge graph queries (Neo4j)
- BKT probability scores
- Affective state signals (frustration/focus)

## Completed Features ✅

### Phase 1: Foundation
- FastAPI backend with CORS
- Groq LLM integration (Llama 3.3 70B)
- Basic hint generation

### Phase 2: Socratic Tutoring
- Python AST code analyzer
- Multi-level hint system (Socratic → Conceptual → Pseudo-code → Direct)
- State machine for intervention timing
- Smart hint generation based on student context

### Phase 3: Viva Voce System
- Audio transcription (Whisper via Groq)
- Question generation from code analysis
- Semantic verification of understanding
- Pass/Weak/Fail verdict system

### Phase 4: Peer Learning System ✅ NEW!
- Student profiling (skill level, learning style, topics)
- Intelligent matching algorithm (complementary skills, shared interests)
- Session management (start, track, end with ratings)
- Role assignment (learner, tutor, peer)

## Next Steps
- [ ] Advanced LangGraph workflow (after integration with Role 1 & 3)
- [ ] AI Problem Generator (convert text to test cases)
- [ ] Integration with WebSocket server (Role 1)
- [ ] Integration with Neo4j knowledge graph (Role 3)
- [ ] Production hardening (auth, rate limiting, monitoring)

## Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key (required) - FREE at console.groq.com | - |
| `GROQ_BASE_URL` | Groq API endpoint | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | Model to use | `llama-3.3-70b-versatile` |

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
Make sure you're running from the `ai-backend` directory and venv is activated.

### "401 Unauthorized" from Groq API
Check that your `GROQ_API_KEY` in `.env` is correct and starts with `gsk_`.

### Port 8000 already in use
Either kill the process using port 8000, or run on a different port:
```bash
uvicorn app.main:app --reload --port 8001
```

## Development Team
**Your Role**: AI Engineer (The Brain)
**Teammates**: Systems Architect (Role 1), Data Architect (Role 3)

---

**Status**: Phases 1-4 Complete ✅
**Version**: 3.0.0
**Next**: Integration with Role 1 & 3, Advanced LangGraph workflows

