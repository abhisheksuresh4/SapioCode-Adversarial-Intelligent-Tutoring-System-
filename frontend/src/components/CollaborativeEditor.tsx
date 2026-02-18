import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react'
import Editor, { OnMount } from '@monaco-editor/react'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { MonacoBinding } from 'y-monaco'
import * as monaco from 'monaco-editor'
import { useEditorStore } from '../store/editorStore'

interface CollaborativeEditorProps {
    roomId: string
    language?: string
    websocketUrl?: string
}

export interface CollaborativeEditorRef {
    getEditorContent: () => string
}

// Generate random user color
const generateUserColor = () => {
    const colors = [
        '#14b8a6', // Teal
        '#8b5cf6', // Purple
        '#f59e0b', // Amber
        '#ec4899', // Pink
        '#3b82f6', // Blue
        '#10b981', // Green
    ]
    return colors[Math.floor(Math.random() * colors.length)]
}

// Generate random user ID
const generateUserId = () => {
    return `user-${Math.random().toString(36).substring(2, 9)}`
}

const CollaborativeEditor = forwardRef<CollaborativeEditorRef, CollaborativeEditorProps>((
    {
        roomId,
        language = 'python',
        websocketUrl = 'ws://localhost:1234'
    },
    ref
) => {
    const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
    const [ydoc] = useState(() => new Y.Doc())
    const [provider, setProvider] = useState<WebsocketProvider | null>(null)
    const [binding, setBinding] = useState<MonacoBinding | null>(null)
    const [userId] = useState(generateUserId())
    const [userColor] = useState(generateUserColor())
    const [errorMessage, setErrorMessage] = useState<string | null>(null)

    const { setConnected, addUser, removeUser } = useEditorStore()

    // Expose getEditorContent method to parent via ref
    useImperativeHandle(ref, () => ({
        getEditorContent: () => {
            return editorRef.current?.getValue() || ''
        }
    }))

    const handleEditorDidMount: OnMount = (editor, monaco) => {
        editorRef.current = editor

        // Create Yjs text type
        const ytext = ydoc.getText('monaco')

        // Create WebSocket provider for collaboration
        const wsProvider = new WebsocketProvider(
            websocketUrl,
            roomId,
            ydoc,
            {
                connect: true,
            }
        )

        // Set up connection status listeners
        wsProvider.on('status', (event: { status: string }) => {
            console.log('WebSocket status:', event.status)
            setConnected(event.status === 'connected')
        })

        // Listen for WebSocket errors (like room full)
        wsProvider.ws?.addEventListener('message', (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'error') {
                    setErrorMessage(data.message)
                    console.error('WebSocket error:', data.message)
                }
            } catch (e) {
                // Not a JSON message, ignore
            }
        })

        wsProvider.ws?.addEventListener('close', (event) => {
            if (event.code === 1008) {
                setErrorMessage('Room is full. Maximum 2 users allowed.')
            }
        })

        // Set up awareness for user presence
        const awareness = wsProvider.awareness
        awareness.setLocalStateField('user', {
            id: userId,
            name: `User ${userId.slice(-4)}`,
            color: userColor,
        })

        // Listen for awareness changes (other users joining/leaving)
        awareness.on('change', () => {
            const states = awareness.getStates()
            states.forEach((state, clientId) => {
                if (state.user && clientId !== awareness.clientID) {
                    addUser(state.user)
                }
            })
        })

        // Create Monaco binding
        const monacoBinding = new MonacoBinding(
            ytext,
            editor.getModel()!,
            new Set([editor]),
            awareness
        )

        setProvider(wsProvider)
        setBinding(monacoBinding)

        // Focus editor
        editor.focus()
    }

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            binding?.destroy()
            provider?.destroy()
            ydoc.destroy()
        }
    }, [binding, provider, ydoc])

    return (
        <div className="h-full w-full relative">
            {errorMessage && (
                <div className="absolute top-0 left-0 right-0 bg-red-500 text-white px-4 py-3 z-50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <span className="font-medium">{errorMessage}</span>
                    </div>
                    <button
                        onClick={() => setErrorMessage(null)}
                        className="text-white hover:text-gray-200"
                    >
                        ✕
                    </button>
                </div>
            )}
            <Editor
                height="100%"
                defaultLanguage={language}
                theme="vs-dark"
                onMount={handleEditorDidMount}
                options={{
                    minimap: { enabled: true },
                    fontSize: 14,
                    lineNumbers: 'on',
                    roundedSelection: true,
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                    wordWrap: 'on',
                    cursorBlinking: 'smooth',
                    cursorSmoothCaretAnimation: 'on',
                    smoothScrolling: true,
                    padding: { top: 16, bottom: 16 },
                }}
            />
        </div>
    )
})

export default CollaborativeEditor
