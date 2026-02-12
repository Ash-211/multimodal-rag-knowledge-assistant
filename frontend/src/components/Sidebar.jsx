import { useState, useRef } from 'react'
import './Sidebar.css'

function Sidebar({ isOpen, documents, onUpload, onDeleteDocument }) {
    const [isDragging, setIsDragging] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(null)
    const fileInputRef = useRef(null)

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
            f.name.endsWith('.docx')
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

    return (
        <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
            <div className="sidebar-content">
                <div className="sidebar-header">
                    <h3>Documents</h3>
                    <span className="doc-count">{documents.length}</span>
                </div>

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
                        accept=".pdf,.txt,.docx"
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
                    <p className="upload-hint">PDF, TXT, DOCX</p>
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
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                                <path d="M14 2v6h6M12 11v6M9 14h6" />
                            </svg>
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
            </div>
        </aside>
    )
}

export default Sidebar
