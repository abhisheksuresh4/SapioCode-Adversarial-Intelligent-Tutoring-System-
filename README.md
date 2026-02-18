# SapioCode - Learning Operating System

A comprehensive EdTech platform that bridges the "Assessment vs. Cognition" gap through collaborative coding, AI-powered Socratic tutoring, and intelligent verification.

## 🚀 Features

- **Real-Time Collaborative Code Editor**: Multi-user editing with CRDT-based synchronization (Yjs)
- **Monaco Editor Integration**: Professional code editor with syntax highlighting
- **User Presence Awareness**: See who's collaborating in real-time
- **Modular Architecture**: Designed for future integration with Judge0, AI tutoring, and more

## 📁 Project Structure

```
SapioCode-Frontend+Backend/
├── frontend/                 # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/      # Reusable components
│   │   │   ├── CollaborativeEditor.tsx
│   │   │   └── UserPresence.tsx
│   │   ├── pages/           # Page components
│   │   │   └── WorkspacePage.tsx
│   │   ├── store/           # Zustand state management
│   │   │   └── editorStore.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
└── websocket-server/        # Node.js WebSocket server for Yjs
    ├── server.js
    └── package.json
```

## 🛠️ Tech Stack

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **TypeScript** - Type safety
- **Monaco Editor** - Code editor (VS Code engine)
- **Yjs** - CRDT for collaborative editing
- **Zustand** - State management
- **Tailwind CSS** - Styling
- **React Router** - Navigation

### Backend (WebSocket Server)
- **Node.js** - Runtime
- **ws** - WebSocket library
- **y-websocket** - Yjs WebSocket provider

## 📦 Installation

### Prerequisites
- Node.js 18+ and npm

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Install WebSocket Server Dependencies

```bash
cd ../websocket-server
npm install
```

## 🚀 Running the Application

### 1. Start the WebSocket Server (Terminal 1)

```bash
cd websocket-server
npm start
```

The server will run on `ws://localhost:1234`

### 2. Start the Frontend Dev Server (Terminal 2)

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 3. Test Collaboration

Open multiple browser windows/tabs at `http://localhost:5173` and start typing in the editor. You'll see changes synchronized in real-time across all instances!

## 🎯 Current Implementation Status

### ✅ Phase 1: Foundation & Collaborative Editor (COMPLETE)
- [x] Project setup with React + Vite + TypeScript
- [x] Monaco Editor integration
- [x] Yjs collaborative editing
- [x] WebSocket server for synchronization
- [x] User presence indicators
- [x] Basic workspace UI layout
- [x] State management with Zustand
- [x] Routing with React Router

### 🔄 Future Phases
- [ ] **Phase 2**: AST parsing, Judge0 integration, Curriculum Navigator
- [ ] **Phase 3**: Socratic AI tutor, Affective computing
- [ ] **Phase 4**: Adversarial fuzzing, Viva Voce oral defense
- [ ] **Phase 5**: Instructor dashboard

## 🏗️ Architecture

### Collaborative Editing Flow

```
User A Browser ←→ WebSocket Server ←→ User B Browser
      ↓                  ↓                    ↓
  Yjs Doc            Yjs Sync             Yjs Doc
      ↓                                       ↓
Monaco Editor                          Monaco Editor
```

### Key Components

1. **CollaborativeEditor.tsx**: Integrates Monaco with Yjs for real-time collaboration
2. **UserPresence.tsx**: Displays connection status and active collaborators
3. **WorkspacePage.tsx**: Main workspace layout with problem statement and editor
4. **editorStore.ts**: Zustand store for global editor state

## 🔧 Configuration

### WebSocket URL
The WebSocket server URL can be configured in `CollaborativeEditor.tsx`:

```typescript
websocketUrl = 'ws://localhost:1234'  // Default
```

### Editor Language
Currently supports Python by default. Can be extended to support:
- JavaScript/TypeScript
- C++
- Java
- And more...

## 📝 Future Integration Points

### Judge0 Code Execution
The architecture is designed to easily integrate Judge0:
- Add execution service in `src/services/`
- Connect "Run Code" and "Submit" buttons
- Display results in the bottom panel

### AI Tutoring
Placeholder for right panel AI chat:
- Will use Groq LLM API
- AST-based context awareness
- Socratic questioning prompts

### Memory Visualizer
Bottom panel ready for:
- Stack frame visualization
- Heap object tracking
- Variable state display

## 🤝 Contributing

This is a research project for educational purposes. Future enhancements will include:
- Academic integrity verification
- Affective computing integration
- Curriculum graph navigation
- Instructor analytics dashboard

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Documentation

- [Product Requirements Document (PRD)](../.gemini/antigravity/brain/1b872de5-f253-4adb-aee7-461b1ce2ebdd/prd.md)
- [Development TODO List](../.gemini/antigravity/brain/1b872de5-f253-4adb-aee7-461b1ce2ebdd/task.md)

---

**Built with ❤️ for better learning outcomes**
