import { useState, useEffect, useRef } from 'react'
import TopNav from './components/TopNav'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'

const API_BASE = 'http://localhost:8000'

function App() {
    const [sidebarOpen, setSidebarOpen] = useState(true)
    const [documents, setDocuments] = useState([])
    const [messages, setMessages] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [token, setToken] = useState(() => localStorage.getItem('token'))
    const [user, setUser] = useState(null)

    // Auth state
    const isAuthenticated = !!token

    // Fetch documents on mount
    useEffect(() => {
        if (isAuthenticated) {
            // Load messages from localStorage if available
            const saved = localStorage.getItem('chat_messages')
            if (saved) {
                try {
                    setMessages(JSON.parse(saved))
                } catch (e) {
                    console.error('Failed to parse saved messages')
                }
            }
        }
    }, [isAuthenticated])

    // Save messages to localStorage
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem('chat_messages', JSON.stringify(messages))
        }
    }, [messages])

    const handleLogin = async (username, password) => {
        try {
            setError(null)
            const formData = new FormData()
            formData.append('username', username)
            formData.append('password', password)

            const res = await fetch(`${API_BASE}/token`, {
                method: 'POST',
                body: formData,
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Login failed')
            }

            const data = await res.json()
            localStorage.setItem('token', data.access_token)
            setToken(data.access_token)
            setUser(username)
        } catch (err) {
            setError(err.message)
            throw err
        }
    }

    const handleRegister = async (username, password) => {
        try {
            setError(null)
            const res = await fetch(`${API_BASE}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Registration failed')
            }

            // Auto-login after registration
            await handleLogin(username, password)
        } catch (err) {
            setError(err.message)
            throw err
        }
    }

    const handleLogout = () => {
        localStorage.removeItem('token')
        localStorage.removeItem('chat_messages')
        setToken(null)
        setUser(null)
        setMessages([])
        setDocuments([])
    }

    const handleUpload = async (file) => {
        try {
            setError(null)
            const formData = new FormData()
            formData.append('file', file)

            // Add optimistic document
            const tempDoc = {
                id: Date.now(),
                name: file.name,
                status: 'uploading',
                progress: 0,
            }
            setDocuments(prev => [...prev, tempDoc])

            const res = await fetch(`${API_BASE}/ingest`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                body: formData,
            })

            if (!res.ok) {
                throw new Error('Upload failed')
            }

            const data = await res.json()

            // Update document status
            setDocuments(prev =>
                prev.map(doc =>
                    doc.id === tempDoc.id
                        ? { ...doc, status: 'ready', chunks: data.chunks, images: data.images }
                        : doc
                )
            )

            return data
        } catch (err) {
            setError(err.message)
            // Update document status to error
            setDocuments(prev =>
                prev.map(doc =>
                    doc.status === 'uploading' ? { ...doc, status: 'error' } : doc
                )
            )
            throw err
        }
    }

    const handleSendMessage = async (content) => {
        if (!content.trim() || isLoading) return

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: content.trim(),
            timestamp: new Date().toISOString(),
        }

        setMessages(prev => [...prev, userMessage])
        setIsLoading(true)
        setError(null)

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ query: content.trim() }),
            })

            if (!res.ok) {
                throw new Error('Failed to get response')
            }

            const data = await res.json()

            const aiMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: data.answer,
                sources: data.sources || [],
                images: data.images || [],
                timestamp: new Date().toISOString(),
            }

            setMessages(prev => [...prev, aiMessage])
        } catch (err) {
            setError(err.message)
            // Add error message
            setMessages(prev => [
                ...prev,
                {
                    id: Date.now() + 1,
                    role: 'error',
                    content: 'Failed to get response. Please try again.',
                    timestamp: new Date().toISOString(),
                },
            ])
        } finally {
            setIsLoading(false)
        }
    }

    const clearChat = () => {
        setMessages([])
        localStorage.removeItem('chat_messages')
    }

    return (
        <div className={`app-layout ${!sidebarOpen ? 'sidebar-collapsed' : ''}`}>
            <TopNav
                user={user}
                isAuthenticated={isAuthenticated}
                onLogin={handleLogin}
                onRegister={handleRegister}
                onLogout={handleLogout}
                onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                sidebarOpen={sidebarOpen}
            />

            <Sidebar
                isOpen={sidebarOpen}
                documents={documents}
                onUpload={handleUpload}
                onDeleteDocument={(id) => setDocuments(prev => prev.filter(d => d.id !== id))}
            />

            <ChatArea
                messages={messages}
                isLoading={isLoading}
                error={error}
                isAuthenticated={isAuthenticated}
                onSendMessage={handleSendMessage}
                onClearChat={clearChat}
                onDismissError={() => setError(null)}
            />
        </div>
    )
}

export default App
