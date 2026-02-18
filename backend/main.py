"""
Simple Code Execution Backend for SapioCode
============================================
This is a DEMO/PROTOTYPE backend that executes user-submitted Python code.

⚠️ SECURITY WARNING ⚠️
This backend runs user code directly on the server using subprocess.
This is ONLY acceptable for:
- Local development/demos
- Controlled environments
- Educational/university projects

In production, you MUST use:
- Sandboxed execution (Docker containers)
- Services like Judge0, Piston, or similar
- Proper resource limits and security isolation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import os
from typing import Optional
import sys

app = FastAPI(title="SapioCode Execution Backend")

# Enable CORS so frontend can call this backend
# ⚠️ In production, restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeExecutionRequest(BaseModel):
    """Request model for code execution"""
    code: str
    stdin: Optional[str] = ""


class CodeExecutionResponse(BaseModel):
    """Response model for code execution"""
    stdout: str
    stderr: str
    exit_code: Optional[int]
    status: str  # "OK" | "RTE" (Runtime Error) | "TLE" (Time Limit Exceeded)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "SapioCode Execution Backend",
        "status": "running",
        "python_version": sys.version,
        "warning": "This is a DEMO service - not for production use!"
    }


@app.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """
    Execute Python code submitted by the user.
    
    ⚠️ SECURITY RISK: This executes arbitrary code on the server!
    Only use for local demos/prototypes.
    """
    
    # Create a temporary file to store the user's code
    # Using a context manager ensures cleanup even if execution fails
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        delete=False,
        encoding='utf-8'
    ) as temp_file:
        temp_file.write(request.code)
        temp_file_path = temp_file.name
    
    try:
        # Execute the code using subprocess
        # timeout=5 means the code will be killed after 5 seconds (TLE)
        result = subprocess.run(
            [sys.executable, temp_file_path],  # Use same Python interpreter
            input=request.stdin,  # Pass stdin to the process
            capture_output=True,  # Capture stdout and stderr
            text=True,  # Return strings instead of bytes
            timeout=5,  # 5 second timeout
            encoding='utf-8',
            errors='replace'  # Replace invalid unicode characters
        )
        
        # Determine status based on exit code
        if result.returncode == 0:
            status = "OK"
        else:
            status = "RTE"  # Runtime Error (non-zero exit code)
        
        return CodeExecutionResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            status=status
        )
    
    except subprocess.TimeoutExpired as e:
        # Code took too long to execute
        return CodeExecutionResponse(
            stdout=e.stdout.decode('utf-8', errors='replace') if e.stdout else "",
            stderr="Execution timed out after 5 seconds",
            exit_code=None,
            status="TLE"  # Time Limit Exceeded
        )
    
    except Exception as e:
        # Unexpected error during execution
        # ⚠️ In production, don't expose internal errors to users
        return CodeExecutionResponse(
            stdout="",
            stderr=f"Internal error: {str(e)}",
            exit_code=None,
            status="RTE"
        )
    
    finally:
        # Clean up: delete the temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SapioCode Backend on http://localhost:8000")
    print("⚠️  WARNING: This server executes arbitrary code - use only for local demos!")
    print("📝 API Docs available at http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
