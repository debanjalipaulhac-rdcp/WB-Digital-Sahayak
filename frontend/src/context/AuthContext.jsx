'use client'

import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)

    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                const stored = localStorage.getItem('wb_user')
                if (stored) setUser(JSON.parse(stored))
            } catch { /* ignore */ }
        }
    }, [])

    function login(userData) {
        setUser(userData)
        if (typeof window !== 'undefined') {
            localStorage.setItem('wb_user', JSON.stringify(userData))
        }
    }

    function logout() {
        setUser(null)
        if (typeof window !== 'undefined') {
            localStorage.removeItem('wb_user')
        }
    }

    return (
        <AuthContext.Provider value={{ user, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be inside AuthProvider')
    return ctx
}
