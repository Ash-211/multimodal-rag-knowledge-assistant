import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import './ChatArea.css'

function ChatArea({
    messages,
    isLoading,
    error,
    isAuthenticated,
    onSendMessage,
    onClearChat,
    onDismissError
}) {
    const [input, setInput] = useState('')
    const messagesEndRef = useRef(null)
    const textareaRef = useRef(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSubmit = (e) => {
        e.preventDefault()
        if (input.trim() && !isLoading) {
            onSendMessage(input)
            setInput('')
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto'
            }
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
        }
    }

    const handleTextareaChange = (e) => {
        setInput(e.target.value)
        // Auto-resize textarea
        e.target.style.height = 'auto'
        e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
    }

    const suggestedQuestions = [
        'What are the key concepts in my documents?',
        'Summarize the main ideas',
        'Find information about...',
        'Compare topics across documents'
    ]

    if (!isAuthenticated) {
        return (
            <main className="chat-area">
                <div className="chat-welcome">
                    <div className="welcome-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                            <path
                                d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                                stroke="url(#welcome-gradient)"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                            <defs>
                                <linearGradient id="welcome-gradient" x1="2" y1="2" x2="22" y2="22">
                                    <stop stopColor="#6366f1" />
                                    <stop offset="1" stopColor="#a855f7" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h1>RAG Knowledge Assistant</h1>
                    <p>Upload documents and ask questions to get AI-powered answers with source citations</p>
                    <div className="welcome-features">
                        <div className="feature-card">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
                            </svg>
                            <h3>Upload Documents</h3>
                            <p>PDF, TXT, DOCX supported</p>
                        </div>
                        <div className="feature-card">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                            </svg>
                            <h3>Ask Questions</h3>
                            <p>Natural language queries</p>
                        </div>
                        <div className="feature-card">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <circle cx="11" cy="11" r="8" />
                                <path d="M21 21l-4.35-4.35" />
                            </svg>
                            <h3>Get Citations</h3>
                            <p>Answers with sources</p>
                        </div>
                    </div>
                    <p className="welcome-cta">Sign in to get started</p>
                </div>
            </main>
        )
    }

    return (
        <main className="chat-area">
            {/* Error Toast */}
            {error && (
                <div className="error-toast animate-fade-in-up">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 8v4M12 16h.01" />
                    </svg>
                    <span>{error}</span>
                    <button
                        className="btn btn-ghost btn-icon"
                        onClick={onDismissError}
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            )}

            {/* Messages Container */}
            <div className="messages-container">
                <div className="messages-wrapper">
                    {messages.length === 0 ? (
                        <div className="chat-empty">
                            <div className="empty-icon">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                                </svg>
                            </div>
                            <h2>Start a Conversation</h2>
                            <p>Upload documents and ask questions about their content</p>

                            <div className="suggested-questions">
                                <p className="suggestions-label">Try asking:</p>
                                <div className="suggestions-grid">
                                    {suggestedQuestions.map((q, i) => (
                                        <button
                                            key={i}
                                            className="suggestion-chip"
                                            onClick={() => setInput(q)}
                                        >
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            {messages.map((msg, index) => (
                                <MessageBubble
                                    key={msg.id}
                                    message={msg}
                                    isLast={index === messages.length - 1}
                                />
                            ))}

                            {isLoading && (
                                <div className="message-row assistant loading">
                                    <div className="message-inner">
                                        <div className="role-icon-wrapper">
                                            <div className="role-icon assistant-icon">
                                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                                                    <path
                                                        d="M12 2L2 7l10 5 10-5-10-5z"
                                                        stroke="currentColor"
                                                        strokeWidth="1.5"
                                                    />
                                                </svg>
                                            </div>
                                        </div>
                                        <div className="message-body">
                                            <div className="typing-indicator">
                                                <span></span>
                                                <span></span>
                                                <span></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="input-area">
                <div className="input-wrapper">
                    {messages.length > 0 && (
                        <button
                            className="btn btn-ghost btn-icon clear-btn"
                            onClick={onClearChat}
                            title="Clear chat"
                        >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                            </svg>
                        </button>
                    )}

                    <form onSubmit={handleSubmit} className="chat-form">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={handleTextareaChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask about your documents..."
                            rows={1}
                            disabled={isLoading}
                            className="chat-input"
                        />
                        <button
                            type="submit"
                            className="btn btn-primary send-btn"
                            disabled={!input.trim() || isLoading}
                        >
                            {isLoading ? (
                                <div className="loading-dots">
                                    <span></span><span></span><span></span>
                                </div>
                            ) : (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                                </svg>
                            )}
                        </button>
                    </form>
                </div>
                <p className="input-hint">Press Enter to send, Shift+Enter for new line</p>
            </div>
        </main>
    )
}

export default ChatArea
