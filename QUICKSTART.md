# SapioCode - Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Start the WebSocket Server

Open a terminal and run:

```bash
cd websocket-server
npm start
```

You should see:
```
🚀 SapioCode WebSocket Server running on ws://localhost:1234
Ready for collaborative editing sessions...
```

### Step 2: Start the Frontend

Open a **new terminal** and run:

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### Step 3: Test Collaboration

1. Open your browser to `http://localhost:3000`
2. Open the same URL in a **new browser window** or **incognito tab**
3. Start typing in the Monaco editor
4. Watch the changes sync in real-time! ✨

## 🎯 What You'll See

- **Top Bar**: Problem title and Run/Submit buttons
- **User Presence Bar**: Connection status and collaborator avatars
- **Left Panel**: Problem description and constraints
- **Center**: Monaco code editor with syntax highlighting
- **Bottom Panel**: Memory visualizer placeholder

## 🧪 Testing Collaboration

Try these actions to test the collaborative features:

1. **Multi-User Editing**: Type simultaneously in both windows
2. **User Presence**: See colored avatars appear in the presence bar
3. **Cursor Tracking**: Watch other users' cursors move (color-coded)
4. **Real-Time Sync**: Changes appear instantly (<100ms)

## 🔧 Troubleshooting

### WebSocket Connection Failed
- Ensure the WebSocket server is running on port 1234
- Check if another process is using port 1234
- Try restarting both servers

### Monaco Editor Not Loading
- Clear browser cache and reload
- Check browser console for errors
- Ensure all npm dependencies are installed

### Changes Not Syncing
- Verify WebSocket connection status (green dot in presence bar)
- Check both browser windows are on the same room/problem ID
- Restart the WebSocket server

### Port Already in Use
- If port 3000 is in use, edit `frontend/vite.config.ts` and change the port number
- Restart the frontend server after making changes

## 📝 Next Steps

Now that the collaborative editor is working, you can:

1. **Customize the UI**: Modify colors, layout in `WorkspacePage.tsx`
2. **Add Languages**: Extend language support in `CollaborativeEditor.tsx`
3. **Integrate Judge0**: Add code execution (see Phase 2 in task.md)
4. **Add AI Tutoring**: Implement Socratic AI (see Phase 3 in task.md)

## 🎨 Customization

### Change Editor Theme
Edit `CollaborativeEditor.tsx`:
```typescript
theme="vs-dark"  // or "vs-light", "hc-black"
```

### Change WebSocket Port
1. Update `websocket-server/server.js`: `const PORT = 1234`
2. Update `CollaborativeEditor.tsx`: `websocketUrl = 'ws://localhost:1234'`

### Change Frontend Port
Edit `frontend/vite.config.ts`:
```typescript
server: {
  port: 3000,  // Change to any available port
  host: true,
}
```

### Change Default Language
Edit `WorkspacePage.tsx`:
```typescript
const [language] = useState('python')  // or 'javascript', 'cpp', 'java'
```

---

**Happy Coding! 🎉**
