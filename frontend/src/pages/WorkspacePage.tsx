import { useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import CollaborativeEditor, { CollaborativeEditorRef } from '../components/CollaborativeEditor'
import UserPresence from '../components/UserPresence'
import CodeOutput from '../components/CodeOutput'
import { executeCode } from '../services/codeExecutionService'
import { useEditorStore } from '../store/editorStore'

const WorkspacePage = () => {
    const { problemId } = useParams<{ problemId: string }>()
    const [language] = useState('python')
    const editorRef = useRef<CollaborativeEditorRef>(null)
    const { setExecutionResult, setIsExecuting, isExecuting } = useEditorStore()

    const handleRunCode = async () => {
        // Get code from editor
        const code = editorRef.current?.getEditorContent()

        if (!code || !code.trim()) {
            alert('Please write some code first!')
            return
        }

        try {
            setIsExecuting(true)

            // Call backend to execute code
            const result = await executeCode(code)

            // Map backend status to our ExecutionStatus type
            const statusMap = {
                'OK': 'success' as const,
                'RTE': 'error' as const,
                'TLE': 'timeout' as const,
            }

            setExecutionResult(
                result.stdout,
                result.stderr,
                statusMap[result.status]
            )
        } catch (error) {
            // Network error or backend not running
            setExecutionResult(
                '',
                error instanceof Error
                    ? `❌ Backend Error: ${error.message}\n\nMake sure the backend server is running on http://localhost:8000`
                    : 'Failed to execute code',
                'error'
            )
        }
    }

    return (
        <div className="h-screen w-screen flex flex-col bg-slate-900">
            {/* Top Bar - Problem Statement */}
            <div className="bg-slate-800 border-b border-slate-700 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-white">
                            {problemId?.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </h1>
                        <p className="text-sm text-gray-400 mt-1">
                            Difficulty: <span className="text-primary-400 font-medium">Medium</span>
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={handleRunCode}
                            disabled={isExecuting}
                            className={`px-4 py-2 rounded-lg transition-colors font-medium flex items-center gap-2 ${isExecuting
                                    ? 'bg-slate-600 text-gray-400 cursor-not-allowed'
                                    : 'bg-slate-700 hover:bg-slate-600 text-white'
                                }`}
                        >
                            {isExecuting ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Running...
                                </>
                            ) : (
                                'Run Code'
                            )}
                        </button>
                        <button className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors font-medium">
                            Submit
                        </button>
                    </div>
                </div>
            </div>

            {/* User Presence Bar */}
            <UserPresence />

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel - Problem Description (Collapsible) */}
                <div className="w-96 bg-slate-800 border-r border-slate-700 overflow-y-auto p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Problem Description</h2>
                    <div className="text-gray-300 space-y-4">
                        <p>
                            Write a function that solves the given problem. Your solution should be efficient
                            and handle edge cases properly.
                        </p>
                        <div className="bg-slate-900 p-4 rounded-lg">
                            <h3 className="text-sm font-semibold text-primary-400 mb-2">Example:</h3>
                            <pre className="text-sm text-gray-300">
                                <code>
                                    {`Input: [1, 2, 3, 4, 5]
Output: [5, 4, 3, 2, 1]`}
                                </code>
                            </pre>
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-white mb-2">Constraints:</h3>
                            <ul className="list-disc list-inside text-sm text-gray-400 space-y-1">
                                <li>1 ≤ array length ≤ 10^5</li>
                                <li>-10^9 ≤ array[i] ≤ 10^9</li>
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Center - Code Editor */}
                <div className="flex-1 flex flex-col">
                    <div className="flex-1 overflow-hidden">
                        <CollaborativeEditor
                            ref={editorRef}
                            roomId={problemId || 'default-room'}
                            language={language}
                        />
                    </div>

                    {/* Bottom Panel - Code Output */}
                    <div className="h-48 border-t border-slate-700">
                        <CodeOutput />
                    </div>
                </div>

                {/* Right Panel - AI Chat (Collapsible, Hidden by Default) */}
                {/* This will be implemented in Phase 3 */}
            </div>
        </div>
    )
}

export default WorkspacePage
