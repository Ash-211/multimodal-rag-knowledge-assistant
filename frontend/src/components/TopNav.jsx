import { useState } from 'react'
import './TopNav.css'

function TopNav({
    user,
    isAuthenticated,
    onLogin,
    onRegister,
    onLogout,
    onToggleSidebar,
    sidebarOpen
}) {
    const [showAuthModal, setShowAuthModal] = useState(false)
    const [authMode, setAuthMode] = useState('login')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError('')

        try {
            if (authMode === 'login') {
                await onLogin(username, password)
            } else {
                await onRegister({ username, password, first_name: firstName, last_name: lastName, email })
            }
            setShowAuthModal(false)
            setUsername('')
            setPassword('')
            setFirstName('')
            setLastName('')
            setEmail('')
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            <nav className="topnav">
                <div className="topnav-left">
                    <button
                        className="btn btn-ghost btn-icon sidebar-toggle"
                        onClick={onToggleSidebar}
                        aria-label="Toggle sidebar"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            {sidebarOpen ? (
                                <path d="M11 19l-7-7 7-7M18 19l-7-7 7-7" />
                            ) : (
                                <path d="M3 12h18M3 6h18M3 18h18" />
                            )}
                        </svg>
                    </button>

                    <div className="topnav-brand">
                        <div className="brand-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                <path
                                    d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                                    stroke="url(#brand-gradient)"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                />
                                <defs>
                                    <linearGradient id="brand-gradient" x1="2" y1="2" x2="22" y2="22">
                                        <stop stopColor="#6366f1" />
                                        <stop offset="1" stopColor="#a855f7" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>
                        <span className="brand-name">VectorMind</span>
                    </div>
                </div>

                <div className="topnav-right">
                    {isAuthenticated ? (
                        <div className="user-menu">
                            <div className="user-avatar">
                                {user?.[0]?.toUpperCase() || 'U'}
                            </div>
                            <span className="user-name">{user}</span>
                            <button className="btn btn-ghost btn-sm" onClick={onLogout}>
                                Logout
                            </button>
                        </div>
                    ) : (
                        <button
                            className="btn btn-primary btn-sm"
                            onClick={() => setShowAuthModal(true)}
                        >
                            Sign In
                        </button>
                    )}
                </div>
            </nav>

            {/* Auth Modal */}
            {showAuthModal && (
                <div className="modal-overlay" onClick={() => setShowAuthModal(false)}>
                    <div className="modal card-glass" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
                            <button
                                className="btn btn-ghost btn-icon"
                                onClick={() => setShowAuthModal(false)}
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M18 6L6 18M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="auth-form">
                            {error && (
                                <div className="auth-error">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="10" />
                                        <path d="M12 8v4M12 16h.01" />
                                    </svg>
                                    {error}
                                </div>
                            )}

                            <div className="form-group">
                                <label htmlFor="username">Username</label>
                                <input
                                    id="username"
                                    type="text"
                                    className="input"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    placeholder="Enter username"
                                    required
                                    autoComplete="username"
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="password">Password</label>
                                <input
                                    id="password"
                                    type="password"
                                    className="input"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="Enter password"
                                    required
                                    autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                                />
                            </div>

                            {authMode === 'register' && (
                                <>
                                    <div className="form-row">
                                        <div className="form-group">
                                            <label htmlFor="firstName">First Name</label>
                                            <input
                                                id="firstName"
                                                type="text"
                                                className="input"
                                                value={firstName}
                                                onChange={e => setFirstName(e.target.value)}
                                                placeholder="First name"
                                                required
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="lastName">Last Name</label>
                                            <input
                                                id="lastName"
                                                type="text"
                                                className="input"
                                                value={lastName}
                                                onChange={e => setLastName(e.target.value)}
                                                placeholder="Last name"
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="email">Email</label>
                                        <input
                                            id="email"
                                            type="email"
                                            className="input"
                                            value={email}
                                            onChange={e => setEmail(e.target.value)}
                                            placeholder="you@example.com"
                                            required
                                        />
                                    </div>
                                </>
                            )}

                            <button
                                type="submit"
                                className="btn btn-primary btn-lg"
                                disabled={loading}
                                style={{ width: '100%' }}
                            >
                                {loading ? (
                                    <span className="loading-dots">
                                        <span></span><span></span><span></span>
                                    </span>
                                ) : authMode === 'login' ? 'Sign In' : 'Create Account'}
                            </button>

                            <div className="auth-switch">
                                {authMode === 'login' ? (
                                    <>
                                        Don't have an account?{' '}
                                        <button type="button" onClick={() => setAuthMode('register')}>
                                            Sign up
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        Already have an account?{' '}
                                        <button type="button" onClick={() => setAuthMode('login')}>
                                            Sign in
                                        </button>
                                    </>
                                )}
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    )
}

export default TopNav
