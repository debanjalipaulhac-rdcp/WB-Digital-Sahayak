'use client'

import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { useLangStore } from '@/stores/lang.store'
import type { Lang } from '@/types'

interface LangOption {
    code: Lang
    label: string
    short: string
}

const LANGS: LangOption[] = [
    { code: 'en', label: 'English', short: 'EN' },
    { code: 'bn', label: 'বাংলা', short: 'বাং' },
    { code: 'hi', label: 'हिंदी', short: 'हि' },
]

interface Props {
    lang?: string
}

export default function LanguageSwitcher({ lang = 'en' }: Props) {
    const { lang: storeLang, setLang } = useLangStore()
    const router = useRouter()
    const [, startTransition] = useTransition()

    // Use Zustand store value if available, otherwise fall back to SSR-passed prop
    const activeLang = storeLang || lang

    const switchLang = (code: Lang) => {
        setLang(code) // writes cookie + updates store
        startTransition(() => router.refresh()) // re-run server components with new lang
    }

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            {LANGS.map(({ code, label, short }) => (
                <button
                    key={code}
                    onClick={() => switchLang(code)}
                    aria-label={`Switch to ${label}`}
                    style={{
                        padding: '5px 10px',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeLang === code ? '600' : '400',
                        background: activeLang === code ? 'var(--color-primary)' : 'transparent',
                        color: activeLang === code ? '#fff' : 'var(--color-muted)',
                        transition: 'all 0.15s ease',
                        minHeight: '32px',
                        minWidth: '44px',
                    }}
                    onMouseEnter={(e) => {
                        if (activeLang !== code) (e.target as HTMLButtonElement).style.background = '#f3f4f6'
                    }}
                    onMouseLeave={(e) => {
                        if (activeLang !== code) (e.target as HTMLButtonElement).style.background = 'transparent'
                    }}
                >
                    {/* Show full labels on desktop, short codes on mobile */}
                    <span className="lang-label-full">{label}</span>
                    <span className="lang-label-short">{short}</span>
                </button>
            ))}
            <style>{`
        .lang-label-short { display: none; }
        @media (max-width: 480px) {
          .lang-label-full { display: none; }
          .lang-label-short { display: inline; }
        }
      `}</style>
        </div>
    )
}
