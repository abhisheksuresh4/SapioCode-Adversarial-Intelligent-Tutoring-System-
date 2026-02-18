/**
 * Code Execution Service
 * 
 * Handles communication with the FastAPI backend for executing user code.
 */

// Backend API URL - adjust if needed
const BACKEND_URL = 'http://localhost:8000'

/**
 * Request payload for code execution
 */
export interface CodeExecutionRequest {
    code: string
    stdin?: string
}

/**
 * Response from code execution backend
 */
export interface CodeExecutionResponse {
    stdout: string
    stderr: string
    exit_code: number | null
    status: 'OK' | 'RTE' | 'TLE'
}

/**
 * Execute Python code using the backend service
 * 
 * @param code - The Python code to execute
 * @param stdin - Optional stdin input for the program
 * @returns Promise with execution results
 * @throws Error if network request fails
 */
export async function executeCode(
    code: string,
    stdin: string = ''
): Promise<CodeExecutionResponse> {
    try {
        const response = await fetch(`${BACKEND_URL}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code,
                stdin,
            }),
        })

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result: CodeExecutionResponse = await response.json()
        return result
    } catch (error) {
        // Network error or backend not running
        throw new Error(
            error instanceof Error
                ? error.message
                : 'Failed to connect to execution backend'
        )
    }
}

/**
 * Check if the backend service is available
 * 
 * @returns Promise<boolean> - true if backend is running
 */
export async function checkBackendHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${BACKEND_URL}/`, {
            method: 'GET',
        })
        return response.ok
    } catch {
        return false
    }
}
