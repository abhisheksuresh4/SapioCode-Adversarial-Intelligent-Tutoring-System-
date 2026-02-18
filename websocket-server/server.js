import { WebSocketServer } from 'ws'
import { setupWSConnection } from 'y-websocket/bin/utils'

const PORT = process.env.PORT || 1234
const MAX_USERS_PER_ROOM = 2

const wss = new WebSocketServer({ port: PORT })

// Track active connections per room
const roomConnections = new Map()

wss.on('connection', (conn, req) => {
    // Extract room name from URL
    const url = new URL(req.url, `http://${req.headers.host}`)
    const roomName = url.pathname.slice(1) // Remove leading '/'

    // Initialize room tracking if it doesn't exist
    if (!roomConnections.has(roomName)) {
        roomConnections.set(roomName, new Set())
    }

    const room = roomConnections.get(roomName)

    // Check if room is full
    if (room.size >= MAX_USERS_PER_ROOM) {
        console.log(`❌ Room "${roomName}" is full (${room.size}/${MAX_USERS_PER_ROOM}). Connection rejected.`)

        // Send error message to client before closing
        conn.send(JSON.stringify({
            type: 'error',
            message: `Room is full. Maximum ${MAX_USERS_PER_ROOM} users allowed.`
        }))

        // Close connection after a short delay
        setTimeout(() => {
            conn.close(1008, 'Room is full')
        }, 100)

        return
    }

    // Add connection to room
    room.add(conn)
    console.log(`✅ New connection to room "${roomName}" (${room.size}/${MAX_USERS_PER_ROOM} users)`)

    // Set up Yjs WebSocket connection
    setupWSConnection(conn, req, {
        gc: true, // Enable garbage collection
    })

    // Handle disconnection
    conn.on('close', () => {
        room.delete(conn)
        console.log(`👋 User left room "${roomName}" (${room.size}/${MAX_USERS_PER_ROOM} users remaining)`)

        // Clean up empty rooms
        if (room.size === 0) {
            roomConnections.delete(roomName)
            console.log(`🧹 Room "${roomName}" cleaned up (empty)`)
        }
    })
})

wss.on('error', (error) => {
    console.error('WebSocket server error:', error)
})

console.log(`🚀 SapioCode WebSocket Server running on ws://localhost:${PORT}`)
console.log(`👥 Room capacity: ${MAX_USERS_PER_ROOM} users per room`)
console.log('Ready for collaborative editing sessions...')

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down WebSocket server...')
    wss.close(() => {
        console.log('✅ Server closed')
        process.exit(0)
    })
})
