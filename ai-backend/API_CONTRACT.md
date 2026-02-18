# SapioCode AI Backend — API Contract

> **Base URL**: `http://localhost:8002`
> **Swagger UI**: `http://localhost:8002/docs`

---

## 1. AI Routes (`/api/ai/`)

### 1.1 `GET /api/ai/status` — Check AI Service
**Response** `200`:
```json
{
  "configured": true,
  "model": "llama-3.3-70b-versatile",
  "phase": 5,
  "features": {
    "basic_hints": true,
    "code_analysis": true,
    "smart_hints": true,
    "intervention_detection": true,
    "viva_voce": true,
    "problem_generation": true,
    "langgraph_workflow": true
  }
}
```

### 1.2 `POST /api/ai/hint` — Basic Socratic Hint
**Request**:
```json
{
  "problem_description": "Write a function to calculate factorial",
  "student_code": "def factorial(n):\n    return n",
  "stuck_duration": 60
}
```
**Response** `200`:
```json
{
  "success": true,
  "hint": "What should happen when n is 0 or 1? Think about the base case.",
  "hint_type": "socratic",
  "stuck_duration": 60
}
```

### 1.3 `POST /api/ai/hint/smart` — Context-Aware Hint
**Request**:
```json
{
  "problem_description": "Find even numbers in a list",
  "student_code": "def find_evens(nums):\n    result = []",
  "time_stuck": 120,
  "frustration_level": 0.6,
  "previous_hints_count": 1,
  "code_attempts": 3
}
```
**Response** `200`:
```json
{
  "success": true,
  "hint": "You have an empty list to store results. How can you check each number?",
  "hint_level": 2,
  "intervention_reason": "Student stuck for 2 minutes with moderate frustration"
}
```

### 1.4 `POST /api/ai/analyze` — Deep AST Code Analysis
**Request**:
```json
{
  "code": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)",
  "language": "python"
}
```
**Response** `200`:
```json
{
  "success": true,
  "language": "python",
  "is_valid": true,
  "summary": "Function 'factorial' with recursion detected",
  "metrics": {
    "functions": 1,
    "loops": 0,
    "variables": 1,
    "complexity": 3,
    "has_recursion": true
  },
  "issues": [],
  "syntax_errors": [],
  "algorithm_pattern": "recursive",
  "function_profiles": [
    {
      "name": "factorial",
      "params": ["n"],
      "has_return": true,
      "is_recursive": true,
      "calls": ["factorial"],
      "complexity": 3
    }
  ]
}
```

### 1.5 `POST /api/ai/generate-test-cases` — Generate Test Cases
**Request**:
```json
{
  "description": "Write a function that reverses a string",
  "difficulty": "easy",
  "num_test_cases": 3
}
```
**Response** `200`:
```json
{
  "success": true,
  "problem": {
    "title": "Reverse a String",
    "description": "...",
    "difficulty": "easy",
    "concepts": ["strings", "iteration"],
    "starter_code": "def reverse_string(s):\n    pass",
    "test_cases": [
      { "input": "hello", "expected_output": "olleh", "is_hidden": false }
    ],
    "hints": ["What does it mean to reverse?", "Think about character positions"]
  }
}
```

---

## 2. Integration Routes (`/api/integration/`)

### 2.1 `POST /api/integration/submit` — Unified Submission Pipeline ⭐
> **This is the main entry point.** It runs the full 9-step pipeline (AST → execution → affect → BKT → hint → persistence).

**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "factorial",
  "code": "def factorial(n):\n    return n",
  "language": "python",
  "frustration_score": 0.3,
  "time_spent_seconds": 120,
  "concept": "recursion"
}
```
**Response** `200`:
```json
{
  "student_id": "alice_001",
  "problem_id": "factorial",
  "analysis": {
    "is_valid": true,
    "algorithm_pattern": "unknown",
    "issues": ["missing_base_case"],
    "function_count": 1,
    "has_recursion": false
  },
  "execution": { "passed": false, "output": "..." },
  "mastery": { "concept": "recursion", "p_mastery": 0.35, "source": "local_bkt" },
  "hint": {
    "should_intervene": true,
    "hint_text": "What should your function do when n reaches 0?",
    "hint_level": 1,
    "teaching_focus": "base_case"
  },
  "affect": { "frustration": 0.3, "engagement": 0.7, "should_intervene": false }
}
```

### 2.2 `POST /api/integration/hint` — Standalone Hint
**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "factorial",
  "code": "def factorial(n):\n    return n",
  "problem_description": "Write a recursive factorial function",
  "frustration_score": 0.5
}
```

### 2.3 `POST /api/integration/hint-graph` — LangGraph-Powered Hint
**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "factorial",
  "code": "def factorial(n):\n    return n",
  "problem_description": "Write a recursive factorial function",
  "frustration_score": 0.5,
  "mastery_level": 0.4,
  "hint_history": []
}
```
**Response** `200`:
```json
{
  "hint_text": "Think about what happens when n is 0...",
  "hint_level": 1,
  "hint_path": "socratic",
  "analysis_summary": "recursive pattern, missing base case",
  "conversation_length": 1
}
```

### 2.4 `POST /api/integration/viva-complete` — Record Viva Result
**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "factorial",
  "concept": "recursion",
  "viva_passed": true,
  "confidence_score": 0.85
}
```

### 2.5 `POST /api/integration/affect` — Update Affect State
**Request**:
```json
{
  "student_id": "alice_001",
  "frustration": 0.4,
  "engagement": 0.7,
  "confusion": 0.2,
  "boredom": 0.1
}
```

### 2.6 `GET /api/integration/student/{student_id}/state` — Get Student State
### 2.7 `GET /api/integration/student/{student_id}/history` — Get Hint History
### 2.8 `GET /api/integration/health` — Integration Health Check

---

## 3. Viva Routes (`/api/viva/`)

### 3.1 `POST /api/viva/start` — Start Viva Session
**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "recursion_basics",
  "code": "def factorial(n):\n    if n == 0: return 1\n    return n * factorial(n-1)"
}
```
**Response** `200`:
```json
{
  "session_id": "550e8400-...",
  "student_id": "alice_001",
  "current_question": "Can you explain what happens when n equals 0?",
  "question_number": 1,
  "total_questions": 3,
  "status": "active"
}
```

### 3.2 `POST /api/viva/answer` — Submit Answer
**Request**:
```json
{
  "session_id": "550e8400-...",
  "answer": "When n is 0, the function returns 1 as the base case"
}
```

### 3.3 `POST /api/viva/verdict/{session_id}` — Get Final Verdict
**Response** `200`:
```json
{
  "verdict": "PASS",
  "overall_score": 0.82,
  "answers_evaluated": 3,
  "total_questions": 3,
  "details": [
    { "question": "...", "answer": "...", "score": 0.9 }
  ]
}
```

### 3.4 `POST /api/viva/transcribe` — Transcribe Audio File
- **Content-Type**: `multipart/form-data`
- **Field**: `file` (audio file: wav, mp3, m4a, webm)

### 3.5 `POST /api/viva/transcribe/base64` — Transcribe Base64 Audio
**Request**:
```json
{
  "audio_data": "base64_encoded_audio...",
  "format": "wav"
}
```

### 3.6 `GET /api/viva/session/{session_id}` — Get Session Status
### 3.7 `GET /api/viva/sessions/{student_id}` — List Student Sessions
### 3.8 `GET /api/viva/health` — Viva System Health

---

## 4. Teacher Routes (`/api/teacher/`)

### 4.1 `GET /api/teacher/class-pulse` — Live Class Snapshot
**Response** `200`:
```json
{
  "timestamp": "2026-02-18T15:30:00Z",
  "active_students": 24,
  "average_mastery": 0.62,
  "average_frustration": 0.28,
  "average_engagement": 0.75,
  "at_risk_count": 3,
  "most_struggled_concept": "recursion"
}
```

### 4.2 `GET /api/teacher/at-risk` — At-Risk Students
**Response** `200`:
```json
[
  {
    "student_id": "bob_002",
    "risk_level": "high",
    "risk_reason": "Low mastery (0.25) + high frustration (0.8)",
    "overall_mastery": 0.25,
    "frustration": 0.8,
    "weak_concepts": ["recursion", "trees"]
  }
]
```

### 4.3 `GET /api/teacher/student/{student_id}/profile` — Student Profile
### 4.4 `GET /api/teacher/student/{student_id}/chat-logs` — Hint History
### 4.5 `GET /api/teacher/mastery-heatmap` — Concept × Student Grid
### 4.6 `GET /api/teacher/students` — List All Students
### 4.7 `POST /api/teacher/generate-problem` — AI Problem Generation

**Request**:
```json
{
  "description": "Write a function that finds the longest common subsequence of two strings",
  "difficulty": "hard",
  "concepts": ["dynamic_programming", "strings"],
  "num_test_cases": 4
}
```
**Response** `200`:
```json
{
  "success": true,
  "problem": {
    "title": "Longest Common Subsequence",
    "description": "...",
    "difficulty": "hard",
    "concepts": ["dynamic_programming", "strings"],
    "starter_code": "def lcs(s1, s2):\n    pass",
    "solution_template": "...",
    "hints": ["Think about overlapping subproblems", "..."],
    "test_cases": [
      { "input": "...", "expected_output": "...", "explanation": "...", "is_hidden": false }
    ]
  }
}
```

---

## 5. Peer Routes (`/api/peer/`)

### 5.1 `POST /api/peer/profile` — Create/Update Peer Profile
### 5.2 `GET /api/peer/profile/{student_id}` — Get Profile
### 5.3 `POST /api/peer/match` — Find Match
### 5.4 `POST /api/peer/session/start` — Start Session
### 5.5 `POST /api/peer/session/{session_id}/end` — End Session
### 5.6 `GET /api/peer/session/{session_id}` — Get Session
### 5.7 `GET /api/peer/sessions/{student_id}` — List Sessions
### 5.8-5.11 — Rate, Stats, Leaderboard, Health

---

## Error Format

All errors follow:
```json
{
  "detail": "Error message here"
}
```

**Status codes**: `200` Success · `400` Bad request · `404` Not found · `500` Server error

---

## Health Check

```bash
curl http://localhost:8002/health
```
```json
{
  "status": "healthy",
  "service": "SapioCode AI Engine",
  "version": "4.0.0"
}
```
