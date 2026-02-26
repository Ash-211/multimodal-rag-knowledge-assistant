import { useState, useRef } from 'react'
import './Sidebar.css'

function Sidebar({
    isOpen,
    isAuthenticated,
    documents,
    conversations,
    activeConversationId,
    onUpload,
    onDeleteDocument,
    onNewChat,
    onSelectConversation,
    onDeleteConversation,
    onClearData
}) {
    const [isDragging, setIsDragging] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(null)
    const [showDocs, setShowDocs] = useState(false)
    const fileInputRef = useRef(null)

    if (!isAuthenticated) {
        return (
            <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
                <div className="sidebar-content" />
            </aside>
        )
    }

    const handleDragOver = (e) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const handleDrop = async (e) => {
        e.preventDefault()
        setIsDragging(false)

        const files = Array.from(e.dataTransfer.files)
        const validFiles = files.filter(f =>
            f.type === 'application/pdf' ||
            f.type === 'text/plain' ||
            f.name.endsWith('.docx') ||
            f.type.startsWith('audio/') ||
            ['.mp3', '.wav', '.m4a', '.ogg', '.flac'].some(ext => f.name.endsWith(ext))
        )

        for (const file of validFiles) {
            try {
                setUploadProgress({ name: file.name, percent: 0 })
                await onUpload(file)
                setUploadProgress(null)
            } catch (err) {
                console.error('Upload failed:', err)
                setUploadProgress(null)
            }
        }
    }

    const handleFileSelect = async (e) => {
        const files = Array.from(e.target.files)
        for (const file of files) {
            try {
                setUploadProgress({ name: file.name, percent: 0 })
                await onUpload(file)
                setUploadProgress(null)
            } catch (err) {
                console.error('Upload failed:', err)
                setUploadProgress(null)
            }
        }
        e.target.value = ''
    }

    const getStatusIcon = (status) => {
        switch (status) {
            case 'uploading':
                return (
                    <div className="status-icon uploading">
                        <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 12a9 9 0 11-6.219-8.56" />
                        </svg>
                    </div>
                )
            case 'ready':
                return (
                    <div className="status-icon ready">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 6L9 17l-5-5" />
                        </svg>
                    </div>
                )
            case 'error':
                return (
                    <div className="status-icon error">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 8v4M12 16h.01" />
                        </svg>
                    </div>
                )
            default:
                return null
        }
    }

    const getFileIcon = (name) => {
        if (name.endsWith('.pdf')) {
            return (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <path d="M14 2v6h6M9 15h6M9 11h6" />
                </svg>
            )
        }
        return (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path d="M14 2v6h6" />
            </svg>
        )
    }

    const getRelativeTime = (timestamp) => {
        if (!timestamp) return ''
        const now = new Date()
        const then = new Date(timestamp)
        const diff = Math.floor((now - then) / 1000)
        if (diff < 60) return 'just now'
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
        if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
        return then.toLocaleDateString()
    }

    return (
        <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
            <div className="sidebar-content">
                {/* New Chat Button */}
                <button className="new-chat-btn" onClick={onNewChat}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 5v14M5 12h14" />
                    </svg>
                    New Chat
                </button>

                {/* Chat History */}
                <div className="chat-history-section">
                    <div className="section-header">
                        <h3>Conversations</h3>
                        {conversations.length > 0 && (
                            <span className="doc-count">{conversations.length}</span>
                        )}
                    </div>

                    <div className="conversation-list">
                        {conversations.length === 0 ? (
                            <div className="empty-conversations">
                                <p>No conversations yet</p>
                                <span>Start chatting to create one</span>
                            </div>
                        ) : (
                            conversations.map((conv) => (
                                <div
                                    key={conv.id}
                                    className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
                                    onClick={() => onSelectConversation(conv.id)}
                                >
                                    <div className="conv-icon">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                                        </svg>
                                    </div>
                                    <div className="conv-info">
                                        <span className="conv-title">{conv.title}</span>
                                        <span className="conv-time">{getRelativeTime(conv.updated_at)}</span>
                                    </div>
                                    <button
                                        className="conv-delete btn btn-ghost btn-icon"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            onDeleteConversation(conv.id)
                                        }}
                                        aria-label="Delete conversation"
                                    >
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="M18 6L6 18M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Documents Section - Collapsible */}
                <div className="documents-section">
                    <div
                        className="section-header clickable"
                        onClick={() => setShowDocs(!showDocs)}
                    >
                        <h3>
                            <svg
                                width="12" height="12"
                                viewBox="0 0 24 24"
                                fill="none" stroke="currentColor" strokeWidth="2"
                                className={`chevron ${showDocs ? 'open' : ''}`}
                            >
                                <path d="M9 18l6-6-6-6" />
                            </svg>
                            Documents
                        </h3>
                        <span className="doc-count">{documents.length}</span>
                    </div>

                    {showDocs && (
                        <>
                            {/* Upload Zone */}
                            <div
                                className={`upload-zone ${isDragging ? 'dragging' : ''}`}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".pdf,.txt,.docx,.mp3,.wav,.m4a,.ogg,.flac"
                                    multiple
                                    onChange={handleFileSelect}
                                    hidden
                                />
                                <div className="upload-icon">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                                    </svg>
                                </div>
                                <p className="upload-text">
                                    {isDragging ? 'Drop files here' : 'Upload documents'}
                                </p>
                                <p className="upload-hint">PDF, TXT, DOCX, MP3, WAV, M4A</p>
                            </div>

                            {/* Upload Progress */}
                            {uploadProgress && (
                                <div className="upload-progress">
                                    <div className="progress-info">
                                        <span className="progress-name">{uploadProgress.name}</span>
                                        <span className="progress-status">Uploading...</span>
                                    </div>
                                    <div className="progress-bar">
                                        <div className="progress-fill animate-pulse" style={{ width: '100%' }} />
                                    </div>
                                </div>
                            )}

                            {/* Document List */}
                            <div className="document-list">
                                {documents.length === 0 ? (
                                    <div className="empty-docs">
                                        <p>No documents yet</p>
                                        <span>Upload files to get started</span>
                                    </div>
                                ) : (
                                    documents.map((doc) => (
                                        <div key={doc.id} className={`document-item ${doc.status}`}>
                                            <div className="doc-icon">{getFileIcon(doc.name)}</div>
                                            <div className="doc-info">
                                                <span className="doc-name">{doc.name}</span>
                                                {doc.chunks && (
                                                    <span className="doc-meta">{doc.chunks} chunks</span>
                                                )}
                                            </div>
                                            {getStatusIcon(doc.status)}
                                            <button
                                                className="doc-delete btn btn-ghost btn-icon"
                                                onClick={() => onDeleteDocument(doc.id)}
                                                aria-label="Delete document"
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M18 6L6 18M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </>
                    )}
                </div>

                {/* Clear All Data */}
                <div className="clear-data-section">
                    <button className="btn btn-ghost btn-sm clear-data-btn" onClick={onClearData}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                        </svg>
                        Clear All Data
                    </button>
                </div>
            </div>
        </aside>
    )
}

export default Sidebar
