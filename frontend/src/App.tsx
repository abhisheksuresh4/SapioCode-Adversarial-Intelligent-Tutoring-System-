import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import WorkspacePage from './pages/WorkspacePage'
import './App.css'

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Navigate to="/workspace/demo-problem" replace />} />
                <Route path="/workspace/:problemId" element={<WorkspacePage />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
