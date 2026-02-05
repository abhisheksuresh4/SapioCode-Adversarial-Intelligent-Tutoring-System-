@echo off
echo ================================
echo SapioCode AI Engine - Starting
echo ================================
echo.

cd /d "%~dp0"

if not exist "venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your Groq API key from https://console.groq.com
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.
echo Press CTRL+C to stop the server
echo.

python -m uvicorn app.main:app --reload --port 8000
