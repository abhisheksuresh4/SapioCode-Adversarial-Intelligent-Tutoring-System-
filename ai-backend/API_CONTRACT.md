# SapioCode AI Backend - Integration Contract

## 📡 Base URL
```
Development: http://localhost:8000
Production: TBD (after deployment)
```

## 🔑 Core Endpoints (MUST IMPLEMENT)

### 1. Generate Hint
**Purpose**: Get a Socratic hint when student is stuck

**Endpoint**: `POST /api/ai/hint`

**Request**:
```json
{
  "problem_description": "Write a function to calculate factorial",
  "student_code": "def factorial(n):\n    return n",
  "stuck_duration": 60
}
```

**Response**:
```json
{
  "success": true,
  "hint": "What happens when n is 0? Think about the base case.",
  "hint_type": "socratic",
  "stuck_duration": 60
}
```

**Notes**:
- `stuck_duration` is optional (defaults to 0)
- Hint will be a question, not a solution

---

### 2. Analyze Code
**Purpose**: Get structural analysis of student's code

**Endpoint**: `POST /api/ai/analyze`

**Request**:
```json
{
  "code": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)",
  "language": "python"
}
```

**Response**:
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
  "syntax_errors": []
}
```

---

### 3. Start Viva Session
**Purpose**: Begin oral examination

**Endpoint**: `POST /api/viva/start`

**Request**:
```json
{
  "student_id": "alice_001",
  "problem_id": "recursion_basics",
  "code": "def factorial(n):\n    if n == 0: return 1\n    return n * factorial(n-1)"
}
```

**Response**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "student_id": "alice_001",
  "problem_id": "recursion_basics",
  "current_question": "Can you explain what happens when n equals 0?",
  "question_number": 1,
  "total_questions": 3,
  "status": "active"
}
```

---

## 🔧 Optional Endpoints (NICE TO HAVE)

### 4. Smart Hint (Advanced)
**Endpoint**: `POST /api/ai/hint/smart`

**Request**:
```json
{
  "problem_description": "Find even numbers",
  "student_code": "def find_evens(nums):\n    result = []",
  "time_stuck": 120,
  "frustration_level": 0.6,
  "previous_hints_count": 1,
  "code_attempts": 3
}
```

**Response**:
```json
{
  "success": true,
  "hint": "Try using a loop to iterate through the list",
  "hint_level": 2,
  "intervention_reason": "Student stuck for 2 minutes with high frustration"
}
```

---

## 🚦 Health Check

### Check AI Service Status
**Endpoint**: `GET /api/ai/status`

**Response**:
```json
{
  "configured": true,
  "model": "llama-3.3-70b-versatile",
  "phase": 2,
  "features": {
    "basic_hints": true,
    "code_analysis": true,
    "smart_hints": true,
    "intervention_detection": true
  }
}
```

---

## ⚠️ Error Handling

All endpoints return errors in this format:

```json
{
  "detail": "Error message here"
}
```

**Common Status Codes**:
- `200`: Success
- `400`: Bad request (invalid input)
- `404`: Resource not found
- `500`: Server error (Groq API issue, etc.)

---

## 📝 Integration Checklist

Before connecting the frontend, verify:

- [ ] Server runs without errors: `uvicorn app.main:app --reload`
- [ ] Swagger docs accessible: http://localhost:8000/docs
- [ ] Health check returns `configured: true`
- [ ] Mock frontend tests pass: `python mock_frontend_test.py`
- [ ] GROQ_API_KEY is set in `.env`

---

## 🤝 Communication Protocol

**When you integrate**:
1. Run the mock tests first
2. If a test fails, send me the exact error message
3. Don't modify the request format - let me know if you need changes
4. Use the Swagger docs for testing: http://localhost:8000/docs

**My availability**:
- I can fix backend issues within 24 hours
- For urgent bugs, message me with the error log

---

## 📚 Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Source Code**: `d:\cognicode\ai-backend\`

---

## 🎓 Example Integration Flow

```javascript
// Frontend Example (JavaScript/React)
async function getHint(code, problemDescription) {
  const response = await fetch('http://localhost:8000/api/ai/hint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      problem_description: problemDescription,
      student_code: code,
      stuck_duration: 60
    })
  });
  
  const data = await response.json();
  return data.hint;
}
```

---

**Last Updated**: 2026-01-29
**Maintained By**: Role 2 (AI Backend)
