# SapioCode Backend - Code Execution Service

A simple Python backend for executing user-submitted code. Built for university project demos.

## ⚠️ Security Warning

**This backend executes arbitrary code directly on the server!**

This is acceptable ONLY for:
- ✅ Local development and demos
- ✅ Controlled educational environments
- ✅ University project presentations

**DO NOT use in production!** In real applications, use:
- Docker containers with resource limits
- Sandboxed execution services (Judge0, Piston, etc.)
- Proper security isolation

---

## Quick Start

### 1. Install Dependencies

Open a terminal in the `backend` folder and run:

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python main.py
```

Or alternatively:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on **http://localhost:8000**

### 3. Test the API

Visit **http://localhost:8000/docs** to see the interactive API documentation (Swagger UI).

---

## API Endpoint

### `POST /run`

Execute Python code.

**Request Body (JSON):**
```json
{
  "code": "print('Hello, World!')",
  "stdin": ""
}
```

**Response (JSON):**
```json
{
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "status": "OK"
}
```

**Status Values:**
- `"OK"` - Code executed successfully (exit code 0)
- `"RTE"` - Runtime Error (non-zero exit code or execution error)
- `"TLE"` - Time Limit Exceeded (execution took longer than 5 seconds)

---

## Frontend Integration Example

### Using Fetch API (Vanilla JavaScript)

```javascript
async function runCode(code, stdin = "") {
  try {
    const response = await fetch("http://localhost:8000/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code: code,
        stdin: stdin,
      }),
    });

    const result = await response.json();
    
    // Handle the response
    console.log("Status:", result.status);
    console.log("stdout:", result.stdout);
    console.log("stderr:", result.stderr);
    console.log("Exit code:", result.exit_code);
    
    // Show output to user
    if (result.status === "OK") {
      console.log("✅ Success!");
      console.log(result.stdout);
    } else if (result.status === "TLE") {
      console.error("⏱️ Time limit exceeded!");
    } else if (result.status === "RTE") {
      console.error("❌ Runtime error!");
      console.error(result.stderr);
    }
    
    return result;
  } catch (error) {
    console.error("Network error:", error);
    throw error;
  }
}

// Example usage:
runCode("print('Hello from SapioCode!')");
```

### Using Axios (if you have it installed)

```javascript
import axios from 'axios';

async function runCode(code, stdin = "") {
  try {
    const response = await axios.post("http://localhost:8000/run", {
      code: code,
      stdin: stdin,
    });

    const result = response.data;
    
    console.log("Status:", result.status);
    console.log("stdout:", result.stdout);
    console.log("stderr:", result.stderr);
    
    return result;
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}
```

### React/TypeScript Example

```typescript
interface CodeExecutionResult {
  stdout: string;
  stderr: string;
  exit_code: number | null;
  status: "OK" | "RTE" | "TLE";
}

async function executeCode(code: string, stdin: string = ""): Promise<CodeExecutionResult> {
  const response = await fetch("http://localhost:8000/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ code, stdin }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Usage in a component:
const handleRunCode = async () => {
  try {
    const result = await executeCode(editorCode, userInput);
    
    if (result.status === "OK") {
      setOutput(result.stdout);
    } else if (result.status === "TLE") {
      setOutput("⏱️ Time limit exceeded (5 seconds)");
    } else {
      setOutput(`Error:\n${result.stderr}`);
    }
  } catch (error) {
    setOutput(`Network error: ${error.message}`);
  }
};
```

---

## Example Test Cases

### 1. Simple Hello World
**Code:**
```python
print("Hello, World!")
```

**Expected Response:**
```json
{
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "status": "OK"
}
```

### 2. With User Input (stdin)
**Code:**
```python
name = input("Enter your name: ")
print(f"Hello, {name}!")
```

**Request:**
```json
{
  "code": "name = input('Enter your name: ')\nprint(f'Hello, {name}!')",
  "stdin": "Alice"
}
```

**Expected Response:**
```json
{
  "stdout": "Enter your name: Hello, Alice!\n",
  "stderr": "",
  "exit_code": 0,
  "status": "OK"
}
```

### 3. Runtime Error
**Code:**
```python
print(1 / 0)
```

**Expected Response:**
```json
{
  "stdout": "",
  "stderr": "Traceback (most recent call last):\n  File ...\nZeroDivisionError: division by zero\n",
  "exit_code": 1,
  "status": "RTE"
}
```

### 4. Time Limit Exceeded
**Code:**
```python
import time
time.sleep(10)  # Will timeout after 5 seconds
```

**Expected Response:**
```json
{
  "stdout": "",
  "stderr": "Execution timed out after 5 seconds",
  "exit_code": null,
  "status": "TLE"
}
```

---

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

---

## Troubleshooting

### Port already in use
If port 8000 is already in use, change it in `main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Use port 8001
```

### CORS errors in browser
The backend is configured to allow all origins for development. If you still see CORS errors:
1. Make sure the backend is running
2. Check the browser console for the exact error
3. Try accessing http://localhost:8000/ directly to verify the server is running

### Module not found errors in user code
The code runs in a clean Python environment. If users need specific packages:
- They must be installed on the server where the backend runs
- In production, use Docker containers with pre-installed packages

---

## Future Improvements (for production)

1. **Sandboxing**: Use Docker containers to isolate code execution
2. **Language support**: Add support for Java, C++, JavaScript, etc.
3. **Resource limits**: Memory limits, CPU limits, disk I/O limits
4. **Queue system**: Use Celery or similar for async execution
5. **Rate limiting**: Prevent abuse
6. **Authentication**: Require API keys or user authentication
7. **Logging**: Track all executions for monitoring and debugging
8. **Test cases**: Automated testing like competitive programming judges

---

## License

This is a student project for educational purposes.
