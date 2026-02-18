@echo off
cd /d D:\cognicode\ai-backend
D:\cognicode\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8002
