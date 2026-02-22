import { useState, useEffect, useRef } from 'react'
import TopNav from './components/TopNav'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function App() {
    const [sidebarOpen, setSidebarOpen] = useState(true)
    const [documents, setDocuments] = useState([])
    const [messages, setMessages] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [token, setToken] = useState(() => localStorage.getItem('token'))
    const [user, setUser] = useState(null)

    // Conversation state
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const isFirstMessage = useRef(true)

    // Auth state
    const isAuthenticated = !!token

    // Fetch documents and conversations on auth
    useEffect(() => {
        if (isAuthenticated) {
            fetchDocuments()
            fetchConversations()
        }
    }, [isAuthenticated])

    // --- Auth ---
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
            // Start with a fresh chat on login
            setMessages([])
            setActiveConversationId(null)
        } catch (err) {
            setError(err.message)
            throw err
        }
    }

    const handleRegister = async ({ username, password, first_name, last_name, email }) => {
        try {
            setError(null)
            const res = await fetch(`${API_BASE}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, first_name, last_name, email }),
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Registration failed')
            }

            await handleLogin(username, password)
        } catch (err) {
            setError(err.message)
            throw err
        }
    }

    const handleLogout = () => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
        setMessages([])
        setDocuments([])
        setConversations([])
        setActiveConversationId(null)
    }

    // --- Conversations ---
    const fetchConversations = async () => {
        try {
            const res = await fetch(`${API_BASE}/conversations`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (res.ok) {
                const data = await res.json()
                setConversations(data.conversations)
            }
        } catch (err) {
            console.error('Failed to fetch conversations:', err)
        }
    }

    const handleNewChat = () => {
        setActiveConversationId(null)
        setMessages([])
        isFirstMessage.current = true
    }

    const handleSelectConversation = async (convId) => {
        if (convId === activeConversationId) return
        setActiveConversationId(convId)
        setMessages([])
        isFirstMessage.current = false

        try {
            const res = await fetch(`${API_BASE}/conversations/${convId}/messages`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (res.ok) {
                const data = await res.json()
                setMessages(data.messages.map((msg, i) => ({
                    id: Date.now() + i,
                    ...msg,
                })))
            }
        } catch (err) {
            console.error('Failed to load conversation:', err)
        }
    }

    const handleDeleteConversation = async (convId) => {
        try {
            await fetch(`${API_BASE}/conversations/${convId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` },
            })
            setConversations(prev => prev.filter(c => c.id !== convId))
            if (activeConversationId === convId) {
                handleNewChat()
            }
        } catch (err) {
            console.error('Failed to delete conversation:', err)
        }
    }

    // --- Data Management ---
    const handleClearData = async () => {
        if (!window.confirm('This will delete ALL of your documents and chat history. Are you sure? '))
            return
        try {
            await fetch(`${API_BASE}/clear-data`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            })
            await fetch(`${API_BASE}/chat/history`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` },
            })
        } catch (err) {
            console.error('Failed to clear data:', err)
        }
        setMessages([])
        setDocuments([])
        setConversations([])
        setActiveConversationId(null)
    }

    // --- Documents ---
    const fetchDocuments = async () => {
        try {
            const res = await fetch(`${API_BASE}/documents`, {
                headers: { Authorization: `Bearer ${token}` },
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

    const handleUpload = async (file) => {
        try {
            setError(null)
            const formData = new FormData()
            formData.append('file', file)

            const tempDoc = {
                id: Date.now(),
                name: file.name,
                status: 'uploading',
                progress: 0,
            }
            setDocuments(prev => [...prev, tempDoc])

            const res = await fetch(`${API_BASE}/ingest`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: (() => {
                    if (activeConversationId) {
                        formData.append('conversation_id', activeConversationId)
                    }
                    return formData
                })(),
            })

            if (!res.ok) throw new Error('Upload failed')

            const data = await res.json()
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
            setDocuments(prev =>
                prev.map(doc =>
                    doc.status === 'uploading' ? { ...doc, status: 'error' } : doc
                )
            )
            throw err
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
        } catch (err) {
            console.error('Failed to delete document: ', err)
        }
    }

    // --- Chat ---
    const handleSendMessage = async (content) => {
        if (!content.trim() || isLoading) return

        // If no active conversation, create one first
        let convId = activeConversationId
        let isNew = false
        if (!convId) {
            try {
                const res = await fetch(`${API_BASE}/conversations`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                })
                const data = await res.json()
                convId = data.id
                setActiveConversationId(convId)
                setConversations(prev => [data, ...prev])
                isNew = true
                isFirstMessage.current = true
            } catch (err) {
                console.error('Failed to create conversation:', err)
                return
            }
        }

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

        // Save user message to backend (await to ensure it's in DB)
        await fetch(`${API_BASE}/chat/history`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ ...userMessage, conversation_id: convId }),
        })

        try {
            const res = await fetch(`${API_BASE}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ query: content.trim(), conversation_id: convId }),
            })

            if (!res.ok) throw new Error('Failed to get response')

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
            let accumulatedContent = ''
            let finalSources = []
            let finalImages = []

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })

                const lines = buffer.split('\n')
                buffer = lines.pop()

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue

                    try {
                        const event = JSON.parse(line.slice(6))

                        if (event.type === 'text') {
                            accumulatedContent += event.content
                            setMessages(prev => prev.map(msg =>
                                msg.id === aiMessageId
                                    ? { ...msg, content: msg.content + event.content }
                                    : msg
                            ))
                        } else if (event.type === 'done') {
                            finalSources = event.sources || []
                            finalImages = event.images || []
                            setMessages(prev => prev.map(msg =>
                                msg.id === aiMessageId
                                    ? { ...msg, sources: finalSources, images: finalImages }
                                    : msg
                            ))
                        } else if (event.type === 'error') {
                            accumulatedContent += '\n\nError: ' + event.content
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
            // Save the final assistant message to backend using local variables
            if (accumulatedContent) {
                fetch(`${API_BASE}/chat/history`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        conversation_id: convId,
                        role: 'assistant',
                        content: accumulatedContent,
                        sources: finalSources,
                        images: finalImages,
                        timestamp: new Date().toISOString(),
                    }),
                })
            }

            // Generate title for new conversations
            if (isFirstMessage.current) {
                isFirstMessage.current = false
                fetch(`${API_BASE}/conversations/${convId}/generate-title`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ message: content.trim() }),
                }).then(res => res.json()).then(data => {
                    setConversations(prev => prev.map(c =>
                        c.id === convId ? { ...c, title: data.title } : c
                    ))
                }).catch(() => { })
            }
        } catch (err) {
            setError(err.message)
            setIsLoading(false)
            setMessages(prev => {
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
        handleNewChat()
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
                isAuthenticated={isAuthenticated}
                documents={documents}
                conversations={conversations}
                activeConversationId={activeConversationId}
                onUpload={handleUpload}
                onDeleteDocument={(id) => {
                    const doc = documents.find(d => d.id === id)
                    if (doc) handleDeleteDocument(id, doc.name)
                }}
                onNewChat={handleNewChat}
                onSelectConversation={handleSelectConversation}
                onDeleteConversation={handleDeleteConversation}
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
