# 🚀 Integration Quickstart for Teammates

> **AI Backend** runs at `http://localhost:8002`
> **Swagger UI**: `http://localhost:8002/docs`

---

## Step 1: Start the AI Server (2 min)

```bash
cd ai-backend
.venv\Scripts\activate          # or: venv\Scripts\activate
uvicorn app.main:app --reload --port 8002
```

Verify: open `http://localhost:8002/docs` — you should see the Swagger UI.

---

## Step 2: The Main Endpoint You Need

### `POST /api/integration/submit` — Unified Submission Pipeline

This is the **single entry point** for all student code submissions. It runs the full pipeline: AST analysis → code execution (Role 1) → affect processing → BKT update (Role 3) → hint generation → persistence.

```bash
curl -X POST http://localhost:8002/api/integration/submit \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "alice_001",
    "problem_id": "factorial",
    "code": "def factorial(n):\n    return n",
    "language": "python",
    "frustration_score": 0.3,
    "time_spent_seconds": 120,
    "concept": "recursion"
  }'
```

**Returns**: analysis results + mastery update + Socratic hint (if needed) + affect state.

---

## Step 3: Other Key Endpoints

### For Role 1 (Systems Architect)

| What you need | Endpoint | Method |
|---------------|----------|--------|
| Submit code for full pipeline | `/api/integration/submit` | POST |
| Get a standalone hint | `/api/integration/hint` | POST |
| Get LangGraph-powered hint | `/api/integration/hint-graph` | POST |
| Update student affect state | `/api/integration/affect` | POST |
| Check student state | `/api/integration/student/{id}/state` | GET |

### For Role 3 (Data Architect)

| What you need | Endpoint | Method |
|---------------|----------|--------|
| Record viva completion | `/api/integration/viva-complete` | POST |
| Get teacher class pulse | `/api/teacher/class-pulse` | GET |
| Get at-risk students | `/api/teacher/at-risk` | GET |
| Get mastery heatmap | `/api/teacher/mastery-heatmap` | GET |

### For Frontend

| What you need | Endpoint | Method |
|---------------|----------|--------|
| Start viva session | `/api/viva/start` | POST |
| Submit viva answer | `/api/viva/answer` | POST |
| Get verdict | `/api/viva/verdict/{session_id}` | POST |
| Transcribe audio | `/api/viva/transcribe` | POST (multipart) |
| Basic hint | `/api/ai/hint` | POST |
| Code analysis | `/api/ai/analyze` | POST |

---

## Step 4: Port Configuration

| Service | Port | Owner |
|---------|------|-------|
| Role 1 Backend (Node.js) | 8000 | Nilesh |
| Role 3 Backend (BKT) | 8001 | Abhishek |
| **Role 2 AI Backend** | **8002** | **Achindra** |

The AI backend will call Role 1 at `http://localhost:8000/run` and Role 3 at `http://localhost:8001/submit`. If those aren't running, it gracefully falls back to local processing.

---

## If Something Breaks

1. Check the terminal for error messages
2. Verify `.env` has `GROQ_API_KEY=gsk_...` set
3. Run `python -m pytest tests/ -v` to check all 193 tests pass
4. Full API docs: see `API_CONTRACT.md`

---

**Role 2 (AI Backend)** — Ready for integration! 🧠
