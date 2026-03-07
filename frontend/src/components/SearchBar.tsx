'use client'

import { useState } from 'react'
import { Search, Mic } from 'lucide-react'
import { useRouter } from 'next/navigation'
import VoiceSearchModal from './VoiceSearchModal'
import CheckEligibilityModal from './CheckEligibilityModal'

interface SearchBarProps {
    defaultQuery?: string
    showEligibilityTrigger?: boolean
}

export default function SearchBar({ defaultQuery = '', showEligibilityTrigger = false }: SearchBarProps) {
    const [query, setQuery] = useState(defaultQuery)
    const [voiceOpen, setVoiceOpen] = useState(false)
    const [eligOpen, setEligOpen] = useState(false)
    const router = useRouter()

    function handleSearch(q?: string) {
        const term = (q || query).trim()
        if (term) router.push('/search?q=' + encodeURIComponent(term))
    }

    return (
        <>
            <div className='flex items-center p-2 gap-2 max-w-xl rounded-xl shadow bg-white text-black justify-center min-w-lg'>
                <Search size={20} color="#1A56DB" style={{ flexShrink: 0 }} />
                <input
                    type="text"
                    placeholder="Search schemes (e.g. scholarship)..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                   
                    className='text-black flex-1 px-2 focus:outline-none'
                />
                <button className="mic-btn" aria-label="Voice search" onClick={() => setVoiceOpen(true)}>
                    <Mic size={18} color="#1A56DB" />
                </button>
                <button className="rounded-lg bg-primary px-4 py-2 text-white" onClick={() => handleSearch()}>
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
                onClick={(e: React.MouseEvent<HTMLAnchorElement>) => { e.preventDefault(); setOpen(true) }}
                style={{ padding: '12px 24px', fontSize: 14, gap: 6, flexShrink: 0, whiteSpace: 'nowrap' }}
            >
                Check Eligibility →
            </a>
            <CheckEligibilityModal isOpen={open} onClose={() => setOpen(false)} />
        </>
    )
}
