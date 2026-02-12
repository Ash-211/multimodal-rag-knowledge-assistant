import { useState } from 'react'
import './MessageBubble.css'

function MessageBubble({ message, isLast }) {
    const [showSources, setShowSources] = useState(false)
    const [selectedImage, setSelectedImage] = useState(null)

    const isUser = message.role === 'user'
    const isError = message.role === 'error'
    const isAssistant = message.role === 'assistant'

    const formatTime = (timestamp) => {
        return new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className={`message-bubble ${message.role} ${isLast ? 'is-last' : ''}`}>
            {/* Avatar */}
            {isAssistant && (
                <div className="assistant-avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path
                            d="M12 2L2 7l10 5 10-5-10-5z"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                        <path
                            d="M2 17l10 5 10-5M2 12l10 5 10-5"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                </div>
            )}

            <div className="message-content">
                {/* Message Text */}
                <div className="message-text">
                    {message.content}
                </div>

                {/* Images */}
                {isAssistant && message.images && message.images.length > 0 && (
                    <div className="message-images">
                        {message.images.map((img, i) => (
                            <button
                                key={i}
                                className="image-thumb"
                                onClick={() => setSelectedImage(img)}
                            >
                                <img
                                    src={img.url}
                                    alt={`Reference image from page ${img.page}`}
                                    loading="lazy"
                                />
                                <span className="image-page">p.{img.page}</span>
                            </button>
                        ))}
                    </div>
                )}

                {/* Sources */}
                {isAssistant && message.sources && message.sources.length > 0 && (
                    <div className="message-sources">
                        <button
                            className="sources-toggle"
                            onClick={() => setShowSources(!showSources)}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                                <path d="M14 2v6h6" />
                            </svg>
                            <span>{message.sources.length} source{message.sources.length !== 1 ? 's' : ''}</span>
                            <svg
                                className={`chevron ${showSources ? 'open' : ''}`}
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <path d="M6 9l6 6 6-6" />
                            </svg>
                        </button>

                        {showSources && (
                            <div className="sources-list">
                                {message.sources.map((source, i) => (
                                    <div key={i} className="source-item">
                                        <div className="source-header">
                                            <span className="source-num">{i + 1}</span>
                                            <span className="source-file">{source.source || 'Document'}</span>
                                            {source.score && (
                                                <span className="source-score">
                                                    {(source.score * 100).toFixed(0)}% match
                                                </span>
                                            )}
                                        </div>
                                        <p className="source-content">{source.content}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Timestamp */}
                <div className="message-time">
                    {formatTime(message.timestamp)}
                </div>
            </div>

            {/* User Avatar */}
            {isUser && (
                <div className="user-avatar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                    </svg>
                </div>
            )}

            {/* Error Icon */}
            {isError && (
                <div className="error-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 8v4M12 16h.01" />
                    </svg>
                </div>
            )}

            {/* Image Modal */}
            {selectedImage && (
                <div className="image-modal" onClick={() => setSelectedImage(null)}>
                    <div className="image-modal-content" onClick={e => e.stopPropagation()}>
                        <button
                            className="modal-close btn btn-ghost btn-icon"
                            onClick={() => setSelectedImage(null)}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                        </button>
                        <img src={selectedImage.url} alt="Full size reference" />
                        <p className="image-caption">Page {selectedImage.page}</p>
                    </div>
                </div>
            )}
        </div>
    )
}

export default MessageBubble
