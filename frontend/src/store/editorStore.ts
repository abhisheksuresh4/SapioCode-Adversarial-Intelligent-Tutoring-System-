import { create } from 'zustand'

export interface User {
    id: string
    name: string
    color: string
}

export type ExecutionStatus = 'idle' | 'running' | 'success' | 'error' | 'timeout'

export interface EditorState {
    code: string
    language: string
    isConnected: boolean
    users: User[]
    // Execution state
    output: string
    errorOutput: string
    executionStatus: ExecutionStatus
    isExecuting: boolean
    // Actions
    setCode: (code: string) => void
    setLanguage: (language: string) => void
    setConnected: (connected: boolean) => void
    addUser: (user: User) => void
    removeUser: (userId: string) => void
    setExecutionResult: (output: string, errorOutput: string, status: ExecutionStatus) => void
    setIsExecuting: (isExecuting: boolean) => void
    clearOutput: () => void
}

export const useEditorStore = create<EditorState>((set) => ({
    code: '# Welcome to SapioCode!\n# Start coding...\n',
    language: 'python',
    isConnected: false,
    users: [],
    output: '',
    errorOutput: '',
    executionStatus: 'idle',
    isExecuting: false,

    setCode: (code) => set({ code }),
    setLanguage: (language) => set({ language }),
    setConnected: (connected) => set({ isConnected: connected }),

    addUser: (user) => set((state) => ({
        users: [...state.users.filter(u => u.id !== user.id), user]
    })),

    removeUser: (userId) => set((state) => ({
        users: state.users.filter(u => u.id !== userId)
    })),

    setExecutionResult: (output, errorOutput, status) => set({
        output,
        errorOutput,
        executionStatus: status,
        isExecuting: false
    }),

    setIsExecuting: (isExecuting) => set({ isExecuting }),

    clearOutput: () => set({
        output: '',
        errorOutput: '',
        executionStatus: 'idle'
    }),
}))
