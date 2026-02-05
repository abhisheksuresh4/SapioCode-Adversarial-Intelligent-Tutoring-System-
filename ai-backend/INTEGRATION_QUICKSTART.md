# 🚀 Quick Start for Teammates

## I'm Ready to Integrate!

My AI backend is complete and tested. Here's how to connect:

### Step 1: Start My Server (2 minutes)

```bash
cd ai-backend
venv\Scripts\python -m uvicorn app.main:app --reload
```

Server will run at: **http://localhost:8000**

### Step 2: Test It Works (1 minute)

Open: **http://localhost:8000/docs**

You should see the Swagger UI with all endpoints.

### Step 3: Try the Core Endpoint (2 minutes)

**Endpoint**: `POST /api/ai/hint`

**Test in Swagger**:
1. Click on `/api/ai/hint`
2. Click "Try it out"
3. Paste this:
```json
{
  "problem_description": "Write a function to calculate factorial",
  "student_code": "def factorial(n):\n    return n"
}
```
4. Click "Execute"

**Expected**: You get a Socratic hint like *"What happens when n is 0?"*

---

## What You Need to Send Me

### For Hint Generation (Core Feature)

```json
POST /api/ai/hint
{
  "problem_description": "string",
  "student_code": "string",
  "stuck_duration": 60  // optional, defaults to 0
}
```

### For Code Analysis

```json
POST /api/ai/analyze
{
  "code": "string",
  "language": "python"  // optional, defaults to "python"
}
```

---

## Full Documentation

- **API Contract**: See `API_CONTRACT.md` (complete reference)
- **Test Script**: Run `python mock_frontend_test.py` (automated tests)
- **Swagger UI**: http://localhost:8000/docs (interactive testing)

---

## If Something Breaks

1. Check the server terminal for error messages
2. Verify `.env` has `GROQ_API_KEY` set
3. Send me the error message - I'll fix it quickly

---

## Contact

**Role 2 (AI Backend)** - Ready to help with integration issues!

**Response Time**: Within 24 hours (usually faster)

---

**TL;DR**: 
1. Start server: `uvicorn app.main:app --reload`
2. Test: http://localhost:8000/docs
3. Integrate: POST to `/api/ai/hint` with code + problem description
4. Questions? Read `API_CONTRACT.md`
