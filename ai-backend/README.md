# SapioCode AI Engine (The Brain) 🧠

**Role 2: The AI Engineer** — Intelligence Cluster for the SapioCode NS-CITS Platform

## Overview

This is the AI backend service powering the **Neuro-Symbolic Collaborative Intelligent Tutoring System**. It implements all four Role 2 deliverables:

| # | Deliverable | Status | SRS Mapping |
|---|-------------|--------|-------------|
| 1 | **Socratic Tutoring** — LangGraph state machine with AST-aware, frustration-adaptive hint generation | ✅ Complete | FR-2, FR-3, FR-6 |
| 2 | **Audio Pipeline** — Whisper (Groq) transcription for Viva Voce oral defense | ✅ Complete | FR-8 |
| 3 | **Semantic Verification** — LLM + deterministic concept-overlap scoring (AST vs transcript) | ✅ Complete | FR-9 |
| 4 | **Teacher Tool** — AI Problem Generator (natural language → structured problems with test cases) | ✅ Complete | — |

**Test suite: 193 tests — all passing ✅**

---

## Quick Start

### 1. Get a FREE Groq API Key
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → API Keys → Create new key
3. Copy the key (starts with `gsk_`)

### 2. Setup
```bash
cd ai-backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then paste your GROQ_API_KEY
```

### 3. Run
```bash
uvicorn app.main:app --reload --port 8002
```

- Swagger UI: **http://localhost:8002/docs**
- Health check: **http://localhost:8002/health**

### 4. Verify
```bash
python -m pytest tests/ -v
```

---

## Architecture

```
ai-backend/
├── app/
│   ├── main.py                     # FastAPI app, 5 routers, CORS, lifecycle
│   ├── api/
│   │   ├── ai_routes.py            # 8 endpoints — hints, analysis, status
│   │   ├── viva_routes.py          # 8 endpoints — viva sessions, transcription
│   │   ├── integration_routes.py   # 8 endpoints — unified pipeline, LangGraph
│   │   ├── teacher_routes.py       # 7 endpoints — dashboard, problem gen
│   │   └── peer_routes.py          # 11 endpoints — matching, sessions
│   ├── core/
│   │   └── config.py               # Pydantic Settings (.env loading)
│   └── services/
│       ├── code_analyzer.py        # Deep AST analysis (9 patterns, 12 issues)
│       ├── ast_tutor.py            # TeachingMoment, TutoringContext, memory
│       ├── tutoring_engine.py      # 4-level hint state machine
│       ├── langgraph_tutoring.py   # Real StateGraph (7 nodes, conditional edges)
│       ├── groq_service.py         # Async Groq LLM client (Llama 3.3 70B)
│       ├── whisper_service.py      # Audio transcription (Whisper v3)
│       ├── viva_engine.py          # Viva Voce: questions, semantic verify, verdict
│       ├── problem_generator.py    # Teacher tool: text → problem + test cases
│       ├── integration_bridge.py   # 9-step orchestrator (Role 1↔2↔3)
│       ├── affect_adapter.py       # Frustration/engagement → hint tone
│       ├── bkt_local.py            # Local BKT engine (mirrors Role 3 math)
│       ├── bkt_engine.py           # BKT remote client
│       ├── session_store.py        # SQLite persistence (sessions, hints, viva)
│       ├── teacher_analytics.py    # Class pulse, at-risk, heatmap
│       └── peer_learning.py        # Peer matching & sessions
├── tests/
│   ├── test_phase1_integration.py      # 31 tests — bridge, BKT, affect
│   ├── test_phase2_ast_tutoring.py     # 45 tests — AST, hints, engine
│   ├── test_phase3_semantic_verification.py # 24 tests — viva, verify
│   ├── test_phase4_teacher_analytics.py    # 26 tests — dashboard, risk
│   ├── test_phase5_new_features.py     # 43 tests — LangGraph, session, overlap
│   └── test_problem_generator.py       # 22 tests — problem gen
├── requirements.txt
├── API_CONTRACT.md          # Full API reference for teammates
├── INTEGRATION_QUICKSTART.md # How to connect frontend/other roles
└── .env.example             # Template for API keys
```

---

## Key Services

### 1. Socratic Tutoring (FR-2, FR-3, FR-6)

The system **never gives direct answers**. It uses a LangGraph `StateGraph` with 7 nodes:

```
receive → analyze → assess ─┬─ gentle_hint    (frustration > 0.7)
                             ├─ socratic_hint  (default)
                             └─ challenge_hint (bored/high mastery)
                             └──────→ deliver
```

Each hint path generates progressively detailed guidance (Level 1 → 4):
1. **Guiding Question** — Socratic prompt
2. **Conceptual Nudge** — Points to the relevant concept
3. **Pseudo-code** — Algorithmic direction
4. **Direct** — Final explicit hint (only after 3+ failed attempts)

### 2. Viva Voce (FR-8, FR-9)

**Audio Pipeline**: Student speaks → Whisper transcribes → AI evaluates

**Semantic Verification**: Two-layer scoring:
- **LLM verification**: Groq compares transcript against AST metadata (algorithm pattern, function profiles, detected issues)
- **Deterministic overlap**: `compute_concept_overlap()` extracts AST concepts and transcript concepts, applies synonym mapping (30+ groups), computes Jaccard score

**Verdict**: PASS (≥0.7) · WEAK (≥0.4) · FAIL (<0.4) · INCONCLUSIVE (<2 answers)

### 3. Integration Bridge

Central orchestrator connecting all 3 roles via a 9-step pipeline:

```
Student submits code
  → Step 1: AST deep analysis (CodeAnalyzer)
  → Step 2: Role 1 sandbox execution (POST /run)
  → Step 3: Affect state processing (AffectAdapter)
  → Step 4: BKT mastery update (Role 3 or local fallback)
  → Step 5: Intervention decision (TutoringEngine)
  → Step 6: Hint generation with full CodeAnalysisResult
  → Step 7: Tone adjustment based on affect
  → Step 8: Teacher analytics recording
  → Step 9: SQLite persistence
```

### 4. Teacher Tool

Converts natural language to structured problems:
```
"Write a function that finds the longest common subsequence"
  → Title, Description, Starter Code, Test Cases, Hints, Solution Template
```

---

## API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/ai/hint` | Basic Socratic hint |
| `POST` | `/api/ai/hint/smart` | Context-aware hint (affect + history) |
| `POST` | `/api/ai/analyze` | Deep AST code analysis |
| `POST` | `/api/ai/generate-test-cases` | Generate test cases from description |
| `POST` | `/api/integration/submit` | **Unified submission pipeline** (main entry) |
| `POST` | `/api/integration/hint` | Standalone hint for student |
| `POST` | `/api/integration/hint-graph` | LangGraph-powered hint |
| `POST` | `/api/integration/viva-complete` | Record viva result → BKT update |
| `POST` | `/api/viva/start` | Start viva session |
| `POST` | `/api/viva/answer` | Submit answer to viva question |
| `POST` | `/api/viva/transcribe` | Transcribe audio (file upload) |
| `GET`  | `/api/teacher/class-pulse` | Live classroom snapshot |
| `GET`  | `/api/teacher/at-risk` | At-risk student list |
| `GET`  | `/api/teacher/mastery-heatmap` | Concept × student grid |
| `POST` | `/api/teacher/generate-problem` | AI problem generation |

See [API_CONTRACT.md](API_CONTRACT.md) for full request/response schemas.

---

## Integration Points

| Role | Service | Protocol | Default URL |
|------|---------|----------|-------------|
| Role 1 (Systems Architect) | Code execution sandbox | HTTP POST `/run` | `http://localhost:8000` |
| Role 3 (Data Architect) | BKT mastery updates | HTTP POST `/submit` | `http://localhost:8001` |
| Frontend | All AI endpoints | HTTP REST | `http://localhost:8002` |

---

## Tech Stack

- **FastAPI** — Async Python web framework
- **Groq API** — LLM inference (Llama 3.3 70B, Whisper v3) — **FREE tier available**
- **LangGraph** — State machine for tutoring workflow
- **Python AST** — Deterministic code structure analysis
- **SQLite** — Session persistence (WAL mode, thread-safe)
- **httpx** — Async HTTP client for cross-role communication
- **Pydantic** — Request/response validation

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | — |
| `GROQ_BASE_URL` | Groq API endpoint | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | LLM model | `llama-3.3-70b-versatile` |
| `AI_PORT` | Server port | `8002` |
| `ROLE1_BACKEND_URL` | Role 1 sandbox URL | `http://localhost:8000` |
| `BKT_BACKEND_URL` | Role 3 BKT URL | `http://localhost:8001` |

---

## Development Team

- **Achindra Sharma (2547105)** — Role 2: AI Engineer (this service)
- **Nilesh Gupta (2547138)** — Role 1: Systems Architect
- **Abhishek Suresh Kumar (2547104)** — Role 3: Data Architect

---

**Status**: All Phases Complete ✅ | **Tests**: 193/193 Passing | **Version**: 4.0.0

