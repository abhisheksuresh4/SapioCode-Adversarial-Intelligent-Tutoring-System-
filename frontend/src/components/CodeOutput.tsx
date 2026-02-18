import { useState } from 'react'
import { useEditorStore } from '../store/editorStore'

const CodeOutput = () => {
    const [activeTab, setActiveTab] = useState<'output' | 'memory'>('output')
    const { output, errorOutput, executionStatus, clearOutput } = useEditorStore()

    // Status badge configuration
    const statusConfig = {
        idle: { text: 'Ready', color: 'bg-gray-600' },
        running: { text: 'Running...', color: 'bg-blue-500 animate-pulse' },
        success: { text: 'Success (OK)', color: 'bg-green-500' },
        error: { text: 'Runtime Error (RTE)', color: 'bg-red-500' },
        timeout: { text: 'Timeout (TLE)', color: 'bg-yellow-500' },
    }

    const currentStatus = statusConfig[executionStatus]

    return (
        <div className="h-full bg-slate-800 border-t border-slate-700 flex flex-col">
            {/* Tab Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700">
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('output')}
                        className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === 'output'
                                ? 'bg-slate-700 text-white'
                                : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Output
                    </button>
                    <button
                        onClick={() => setActiveTab('memory')}
                        className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === 'memory'
                                ? 'bg-slate-700 text-white'
                                : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Memory Visualizer
                    </button>
                </div>
                <div className="flex items-center gap-3">
                    {/* Status Badge */}
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">Status:</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium text-white ${currentStatus.color}`}>
                            {currentStatus.text}
                        </span>
                    </div>
                    {/* Clear Button */}
                    {(output || errorOutput) && (
                        <button
                            onClick={clearOutput}
                            className="text-xs text-gray-400 hover:text-white transition-colors"
                            title="Clear output"
                        >
                            Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-auto p-4">
                {activeTab === 'output' ? (
                    <div className="font-mono text-sm">
                        {/* No output message */}
                        {!output && !errorOutput && executionStatus === 'idle' && (
                            <div className="text-gray-500 italic">
                                Click "Run Code" to see output here...
                            </div>
                        )}

                        {/* Stdout */}
                        {output && (
                            <div className="mb-4">
                                <div className="text-xs text-gray-400 mb-1">stdout:</div>
                                <pre className="whitespace-pre-wrap text-green-400 bg-slate-900 p-3 rounded">
                                    {output}
                                </pre>
                            </div>
                        )}

                        {/* Stderr */}
                        {errorOutput && (
                            <div>
                                <div className="text-xs text-gray-400 mb-1">stderr:</div>
                                <pre className="whitespace-pre-wrap text-red-400 bg-slate-900 p-3 rounded">
                                    {errorOutput}
                                </pre>
                            </div>
                        )}

                        {/* Running state */}
                        {executionStatus === 'running' && !output && !errorOutput && (
                            <div className="flex items-center gap-2 text-blue-400">
                                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span>Executing code...</span>
                            </div>
                        )}
                    </div>
                ) : (
                    // Memory Visualizer Tab (Placeholder)
                    <div className="text-gray-400 text-sm">
                        <h3 className="font-semibold text-white mb-2">Memory Visualizer</h3>
                        <p>Stack and heap visualization will appear here during execution...</p>
                        <div className="mt-4 text-xs text-gray-500">
                            (This feature is planned for a future update)
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default CodeOutput
