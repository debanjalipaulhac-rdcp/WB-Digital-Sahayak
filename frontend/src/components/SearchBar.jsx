'use client'

import { useState } from 'react'
import { Search, Mic } from 'lucide-react'
import { useRouter } from 'next/navigation'
import VoiceSearchModal from './VoiceSearchModal'
import CheckEligibilityModal from './CheckEligibilityModal'

export default function SearchBar({ defaultQuery = '', showEligibilityTrigger = false }) {
    const [query, setQuery] = useState(defaultQuery)
    const [voiceOpen, setVoiceOpen] = useState(false)
    const [eligOpen, setEligOpen] = useState(false)
    const router = useRouter()

    function handleSearch(q) {
        const term = (q || query).trim()
        if (term) router.push('/search?q=' + encodeURIComponent(term))
    }

    return (
        <>
            <div style={{
                background: '#fff',
                borderRadius: 16,
                maxWidth: 600,
                margin: '0 auto 20px',
                padding: '6px 6px 6px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
            }}>
                <Search size={20} color="#1A56DB" style={{ flexShrink: 0 }} />
                <input
                    type="text"
                    placeholder="Search schemes (e.g. scholarship)..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    style={{
                        flex: 1, border: 'none', outline: 'none',
                        fontSize: 15, color: 'var(--color-text)',
                        background: 'transparent', minWidth: 0, padding: '8px 0',
                    }}
                />
                <button className="mic-btn" aria-label="Voice search" onClick={() => setVoiceOpen(true)}>
                    <Mic size={18} color="#1A56DB" />
                </button>
                <button className="search-btn" onClick={() => handleSearch()}>
                    Search
                </button>
            </div>

            <VoiceSearchModal isOpen={voiceOpen} onClose={() => setVoiceOpen(false)} />
            {showEligibilityTrigger && (
                <CheckEligibilityModal isOpen={eligOpen} onClose={() => setEligOpen(false)} />
            )}
        </>
    )
}

export function EligibilityTrigger() {
    const [open, setOpen] = useState(false)
    return (
        <>
            <a
                href="#"
                className="btn-primary"
                onClick={(e) => { e.preventDefault(); setOpen(true) }}
                style={{ padding: '12px 24px', fontSize: 14, gap: 6, flexShrink: 0, whiteSpace: 'nowrap' }}
            >
                Check Eligibility →
            </a>
            <CheckEligibilityModal isOpen={open} onClose={() => setOpen(false)} />
        </>
    )
}
