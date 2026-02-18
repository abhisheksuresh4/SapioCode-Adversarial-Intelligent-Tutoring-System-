# SapioCode - Project Overview & File Guide

This document provides a summary of all work completed to date and explains the purpose and importance of every key file in the project.

## ✅ Project Status: What Was Done

We have successfully built the **Foundation** and **Real-Time Collaboration** phases of SapioCode.

### Key Features Implemented:
1.  **Collaborative Code Editor**:
    *   Integrated **Monaco Editor** (VS Code's core) for a professional coding experience.
    *   Implemented **Yjs** for conflict-free, real-time code synchronization.
    *   Added multi-user cursors and selection tracking (color-coded per user).

2.  **Custom WebSocket Server**:
    *   Built a dedicated Node.js server to coordinate collaboration rooms.
    *   **Feature**: Enforced a **2-User Limit** per room. Using more than 2 tabs/browsers will trigger a "Room is full" error, protecting the session quality.
    *   Handles "rooms" dynamically based on the URL (e.g., `/workspace/problem-1` creates a room named `problem-1`).

3.  **Frontend Infrastructure**:
    *   Set up a modern **React + Vite + TypeScript** environment.
    *   Configured **Tailwind CSS** for rapid, professional styling (dark mode enabled).
    *   Implemented **Zustand** for global state management (tracking user presence, connection status).
    *   **Port Config**: Moved frontend to port `3000` to avoid conflicts with your existing projects.

---

## 📂 File Structure & Importance

Here is a breakdown of the project files and why they matter:

### 1. Root Directory (`/`)
*   **`README.md`**: The main entry point. Contains installation and running instructions.
*   **`QUICKSTART.md`**: A simplified 3-step guide to get everything running in seconds.
*   **`PROJECT_OVERVIEW.md`**: (This file) A detailed record of the implementation.

### 2. WebSocket Server (`/websocket-server`)
This is the "traffic controller" for collaboration.

*   **`server.js`** (**CRITICAL**): 
    *   The backend logic.
    *   It accepts WebSocket connections.
    *   **Logic**: It checks if a room has < 2 users. If yes, it allows the connection. If no, it rejects with a "Room is full" message.
    *   It relays Yjs updates between clients so everyone sees the same code.
*   **`package.json`**: Lists dependencies like `ws` (WebSockets) and `y-websocket`.

### 3. Frontend (`/frontend`)
The user-facing application.

#### Configuration Files (Root of frontend)
*   **`vite.config.ts`**: 
    *   Configures the build tool (Vite).
    *   **Importance**: We modified this to set `server.port: 3000` to fix the port conflict you experienced.
*   **`tailwind.config.js`**:
    *   Configures the styling system.
    *   **Importance**: Defines our custom color palette (Teal for focus, Red for frustration).

#### Source Code (`/frontend/src`)
*   **`main.tsx`**: The entry point that mounts React to the DOM.
*   **`App.tsx`**: 
    *   Handles **Routing**. 
    *   It decides that if you go to `/workspace/:id`, it loads the `WorkspacePage`.

#### Components (`/frontend/src/components`)
*   **`CollaborativeEditor.tsx`** (**CRITICAL**):
    *   **Most complex file.**
    *   Initializes the Monaco Editor.
    *   Connects to the WebSocket server (`ws://localhost:1234`).
    *   Binds the editor content to a Yjs document (doing the magic sync).
    *   Handles the "Room Full" error message display.
*   **`UserPresence.tsx`**:
    *   The bar at the top showing "Connected" status and the avatars of other users in the room.

#### Pages (`/frontend/src/pages`)
*   **`WorkspacePage.tsx`**:
    *   The main layout (Top bar, Left description panel, Center editor, Bottom visualizer).
    *   If you want to change the layout (e.g., move the description to the right), this is where you do it.

#### Store (`/frontend/src/store`)
*   **`editorStore.ts`**:
    *   **State Management**.
    *   Keeps track of "Who is online?" and "Are we connected?".
    *   Allows different components (like the Top Bar and the Editor) to talk to each other.

#### Types (`/frontend/src/types`)
*   **`y-monaco.d.ts`**:
    *   A helper file to make TypeScript happy with the Yjs-Monaco binding library (which doesn't have built-in types).

---

## 🚀 How It All Connects

1.  User opens **browser** (`App.tsx` routes to `WorkspacePage`).
2.  `WorkspacePage` loads `CollaborativeEditor`.
3.  `CollaborativeEditor` contacts **`server.js`** via WebSocket.
4.  **`server.js`** checks if room has space (Limit: 2).
5.  If accepted, your keystrokes are sent to **Server** -> **Other User**.
6.  **`UserPresence.tsx`** listens for updates and shows the other user's avatar.

## 🔮 Next Steps (From TODO)
*   **Judge0**: Execute the code (Run/Submit).
*   **AI Tutor**: Add the Socratic chat bot on the right.
*   **Audio**: Implement the Viva Voce defense.
