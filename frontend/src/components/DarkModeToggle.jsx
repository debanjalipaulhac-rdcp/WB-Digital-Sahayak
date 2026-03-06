'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

export default function DarkModeToggle() {
    const [dark, setDark] = useState(false)

    useEffect(() => {
        // Apply on mount immediately
        const stored = typeof window !== 'undefined' ? localStorage.getItem('wb_theme') : null
        const prefersDark = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
        const isDark = stored === 'dark' || (!stored && prefersDark)
        setDark(isDark)
        if (isDark) document.documentElement.classList.add('dark')
        else document.documentElement.classList.remove('dark')
    }, [])

    function toggle() {
        const newDark = !dark
        setDark(newDark)
        if (newDark) {
            document.documentElement.classList.add('dark')
            localStorage.setItem('wb_theme', 'dark')
        } else {
            document.documentElement.classList.remove('dark')
            localStorage.setItem('wb_theme', 'light')
        }
    }

    return (
        <button
            onClick={toggle}
            className="dark-toggle"
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            style={{ position: 'relative' }}
        >
            <Moon size={18} color="#374151" className="icon-moon" />
            <Sun size={18} color="#FCD34D" className="icon-sun" />
        </button>
    )
}
