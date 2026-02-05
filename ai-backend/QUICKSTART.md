# 🚀 Quick Start - Get Your AI Engine Running in 5 Minutes!

## Step 1: Get FREE Groq API Key (2 minutes)

1. Open your browser: **https://console.groq.com**
2. Click "Sign Up" (use Google/GitHub for fastest signup)
3. Once logged in, click **"API Keys"** in the left sidebar
4. Click **"Create API Key"**
5. Give it a name like "SapioCode"
6. Click **"Create"**
7. **Copy the key** - it starts with `gsk_`

**Note**: Groq is 100% FREE with generous rate limits! ⚡

---

## Step 2: Add Your API Key (1 minute)

1. In VS Code, open: `d:\sapiocode\ai-backend\.env`
2. Replace this line:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```
   
   With your actual key:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_from_groq_here
   ```

3. Save the file (Ctrl+S)

---

## Step 3: Start the Server (30 seconds)

**Option A - Using Batch File (Easiest):**
```bash
cd d:\sapiocode\ai-backend
start.bat
```

**Option B - Manual:**
```bash
cd d:\sapiocode\ai-backend
python -m uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## Step 4: Test It! (1 minute)

### Option A - Browser (Interactive)
1. Open: **http://localhost:8000/docs**
2. Click on **POST /api/ai/test**
3. Click **"Try it out"**
4. Replace the example with:
   ```json
   {
     "message": "Explain recursion in one sentence"
   }
   ```
5. Click **"Execute"**

You should see a response from the AI! 🎉

### Option B - VS Code REST Client
1. Open: `test.http`
2. Click on **"Send Request"** above any test

---

## What You Can Do Now ✅

- ✅ Test AI connection: `POST /api/ai/test`
- ✅ Generate Socratic hints: `POST /api/ai/hint`
- ✅ Check service status: `GET /api/ai/status`
- ✅ View all endpoints: http://localhost:8000/docs

---

## Troubleshooting 🔧

### Server won't start
- Make sure virtual environment is activated: `.\venv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`

### 401 Unauthorized Error
- Your API key is wrong
- Make sure it starts with `gsk_`
- Get a new key from https://console.groq.com/keys

### Port 8000 already in use
- Stop any running server (Ctrl+C)
- Or use different port: `python -m uvicorn app.main:app --port 8001`

---

## What's Next? 🎯

**Phase 2 Tomorrow**: Build the LangGraph state machine for intelligent intervention timing!

For detailed documentation, see [README.md](README.md)
