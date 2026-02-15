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
            fetchDocuments()
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

    const handleClearData = async () => {
        if (!window.confirm('This will delete ALL of your documents and chat history. Are you sure? '))
            return
        try {
            await fetch(`${API_BASE}/clear-data`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`
                },
            })
        } catch (err) {
            console.error('Failed to clear data:', err)
        }
        setMessages([])
        setDocuments([])
        localStorage.removeItem('chat_messages')
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
            await fetchDocuments()

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
    const fetchDocuments = async () => {
        try {
            const res = await fetch(`${API_BASE}/documents`, {
                headers: {
                    Authorization: `Bearer ${token}`
                },
            })
            if (res.ok) {
                const data = await res.json()
                setDocuments(data.documents.map((doc, i) => ({
                    id: doc.name + i,
                    name: doc.name,
                    size: doc.size,
                    status: 'ready'
                })))
            }
        } catch (err) {
            console.error('Failed to fetch documents:', err)
        }
    }
    const handleDeleteDocument = async (docId, docName) => {
        try {
            const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docName)}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` },
            })
            if (res.ok) {
                setDocuments(prev => prev.filter(d => d.id !== docId))
            }
        }
        catch (err) {
            console.error('Failed to delete document: ', err)
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

        const aiMessageId = Date.now() + 1

        setMessages(prev => [...prev, userMessage])
        setIsLoading(true)
        setError(null)

        try {
            const res = await fetch(`${API_BASE}/chat/stream`, {
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

            // Response arrived — replace typing indicator with the streaming message
            setIsLoading(false)
            setMessages(prev => [...prev, {
                id: aiMessageId,
                role: 'assistant',
                content: '',
                sources: [],
                images: [],
                timestamp: new Date().toISOString(),
            }])

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })

                // Parse SSE lines from buffer
                const lines = buffer.split('\n')
                buffer = lines.pop() // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue

                    try {
                        const event = JSON.parse(line.slice(6))

                        if (event.type === 'text') {
                            // Append text chunk to the assistant message
                            setMessages(prev => prev.map(msg =>
                                msg.id === aiMessageId
                                    ? { ...msg, content: msg.content + event.content }
                                    : msg
                            ))
                        } else if (event.type === 'done') {
                            // Attach sources and images
                            setMessages(prev => prev.map(msg =>
                                msg.id === aiMessageId
                                    ? { ...msg, sources: event.sources || [], images: event.images || [] }
                                    : msg
                            ))
                        } else if (event.type === 'error') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === aiMessageId
                                    ? { ...msg, content: msg.content + '\n\nError: ' + event.content }
                                    : msg
                            ))
                        }
                    } catch (e) {
                        // Skip unparseable lines
                    }
                }
            }
        } catch (err) {
            setError(err.message)
            setIsLoading(false)
            setMessages(prev => {
                // Remove empty assistant message and add error
                const filtered = prev.filter(m => m.id !== aiMessageId || m.content)
                return [...filtered, {
                    id: Date.now() + 2,
                    role: 'error',
                    content: 'Failed to get response. Please try again.',
                    timestamp: new Date().toISOString(),
                }]
            })
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
                onDeleteDocument={(id) => {
                    const doc = documents.find(d => d.id === id)
                    if (doc) handleDeleteDocument(id, doc.name)
                }}
                onClearData={handleClearData}
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
