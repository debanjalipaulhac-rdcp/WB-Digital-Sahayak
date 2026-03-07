'use client'

import { useState } from 'react'
import { Landmark, LogIn, LogOut, User, FileText } from 'lucide-react'
import { usePathname } from 'next/navigation'
import LanguageSwitcher from './LanguageSwitcher'
import DarkModeToggle from './DarkModeToggle'
import { useUIStore } from '@/stores/ui.store'
import { useAuth } from '@/hooks/useAuth'
import translations from '@/lib/i18n'
import Link from 'next/link'

interface NavLink {
    href: string
    label: string
}

const NAV_LINKS: NavLink[] = [
    { href: '/', label: 'Home' },
    { href: '/schemes', label: 'Schemes' },
    { href: '/applications', label: 'My Applications' },
    { href: '/support', label: 'Support' },
]

function getInitials(name: string = ''): string {
    return name.trim().split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
}

interface NavbarProps {
    lang?: string
    // User is fetched server-side in layout.tsx and passed here as a prop
    user: { name: string | null; phone: string; has_profile: boolean } | null
}

export default function Navbar({ lang = 'en', user }: NavbarProps) {
    const tx = translations[lang] || translations['en']
    const pathname = usePathname()
    const { openModal } = useUIStore()
    const { logout } = useAuth()
    const [dropOpen, setDropOpen] = useState(false)

    async function handleLogout() {
        setDropOpen(false)
        await logout()
    }

    return (
        <nav style={{
            position: 'sticky', top: 0, zIndex: 100,
            background: 'var(--color-surface, #fff)',
            borderBottom: '1px solid var(--color-border)',
            height: 64,
            display: 'flex', alignItems: 'center',
            padding: '0 20px',
            justifyContent: 'space-between',
            gap: 12,
        }}>

            {/* Logo */}
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit', flexShrink: 0 }}>
                <div style={{ width: 40, height: 40, background: 'var(--color-primary)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Landmark size={20} color="white" strokeWidth={2} />
                </div>
                <div>
                    <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--color-text)', lineHeight: 1.2 }}>WB Digital Sahayak</div>
                    <div className="nav-subtitle" style={{ fontSize: 11, color: 'var(--color-muted)', lineHeight: 1 }}>
                        Government of West Bengal
                    </div>
                </div>
            </Link>

            {/* Center nav links (desktop) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} className="nav-subtitle">
                {NAV_LINKS.map(link => (
                    <Link key={link.href} href={link.href} style={{
                        padding: '6px 12px', borderRadius: 8,
                        fontSize: 14, fontWeight: 500,
                        textDecoration: 'none',
                        color: pathname === link.href ? '#1A56DB' : 'var(--color-muted)',
                        background: pathname === link.href ? '#EFF6FF' : 'transparent',
                        transition: 'all 0.15s',
                    }}>
                        {link.label}
                    </Link>
                ))}
            </div>

            {/* Right side */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <LanguageSwitcher lang={lang} />
                <DarkModeToggle />

                {user ? (
                    <div style={{ position: 'relative' }}>
                        <button
                            onClick={() => setDropOpen(o => !o)}
                            style={{
                                width: 38, height: 38, borderRadius: '50%',
                                background: '#EEF2FF', border: 'none', cursor: 'pointer',
                                fontWeight: 700, fontSize: 14, color: '#1A56DB',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}
                        >
                            {getInitials(user.name ?? user.phone)}
                        </button>

                        {dropOpen && (
                            <div style={{
                                position: 'absolute', top: 44, right: 0, width: 180,
                                background: 'var(--color-surface, #fff)',
                                border: '1px solid var(--color-border)',
                                borderRadius: 12, boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
                                overflow: 'hidden', zIndex: 200,
                            }}>
                                <Link href="/profile" onClick={() => setDropOpen(false)} style={{
                                    display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
                                    textDecoration: 'none', color: 'var(--color-text)', fontSize: 14, fontWeight: 500,
                                    borderBottom: '1px solid var(--color-border)',
                                }}>
                                    <User size={16} color="var(--color-muted)" /> My Profile
                                </Link>
                                <Link href="/applications" onClick={() => setDropOpen(false)} style={{
                                    display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
                                    textDecoration: 'none', color: 'var(--color-text)', fontSize: 14, fontWeight: 500,
                                    borderBottom: '1px solid var(--color-border)',
                                }}>
                                    <FileText size={16} color="var(--color-muted)" /> My Applications
                                </Link>
                                <button onClick={handleLogout} style={{
                                    display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
                                    width: '100%', border: 'none', background: 'none', cursor: 'pointer',
                                    color: '#C81E1E', fontSize: 14, fontWeight: 500, textAlign: 'left',
                                }}>
                                    <LogOut size={16} /> Sign Out
                                </button>
                            </div>
                        )}
                    </div>
                ) : (
                    <button
                        onClick={() => openModal('auth')}
                        className="nav-login-btn"
                    >
                        <LogIn size={15} />
                        <span className="login-text">LOGIN</span>
                    </button>
                )}
            </div>
        </nav>
    )
}
