'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface Props {
    defaultQuery?: string
}

export default function SearchInputClient({ defaultQuery = '' }: Props) {
    const [query, setQuery] = useState(defaultQuery)
    const router = useRouter()

    function handleSearch() {
        const q = query.trim()
        if (q) router.push('/search?q=' + encodeURIComponent(q))
    }

    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 0,
            background: '#fff', borderRadius: 12,
            maxWidth: 580, margin: '0 auto',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            overflow: 'hidden',
        }}>
            <Search size={18} color="#9CA3AF" style={{ flexShrink: 0, marginLeft: 16 }} />
            <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Search schemes..."
                style={{
                    flex: 1, border: 'none', outline: 'none',
                    padding: '14px 12px', fontSize: 15, color: '#111928',
                    background: 'transparent',
                }}
            />
            <button onClick={handleSearch} style={{
                background: '#1A56DB', color: '#fff', border: 'none',
                padding: '14px 20px', fontWeight: 600, fontSize: 14,
                cursor: 'pointer', whiteSpace: 'nowrap',
            }}>
                Search
            </button>
        </div>
    )
}
