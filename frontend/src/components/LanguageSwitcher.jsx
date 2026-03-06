'use client'

import { useRouter } from 'next/navigation'

const LANGS = [
    { code: 'en', label: 'English', short: 'EN' },
    { code: 'bn', label: 'বাংলা', short: 'বাং' },
    { code: 'hi', label: 'हिंदी', short: 'हि' },
]

export default function LanguageSwitcher({ lang = 'en' }) {
    const router = useRouter()

    const switchLang = (code) => {
        document.cookie = `wb_lang=${code}; path=/; max-age=31536000; SameSite=Lax`
        router.refresh()
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
                        fontWeight: lang === code ? '600' : '400',
                        background: lang === code ? 'var(--color-primary)' : 'transparent',
                        color: lang === code ? '#fff' : 'var(--color-muted)',
                        transition: 'all 0.15s ease',
                        minHeight: '32px',
                        minWidth: '44px',
                    }}
                    onMouseEnter={(e) => {
                        if (lang !== code) e.target.style.background = '#f3f4f6'
                    }}
                    onMouseLeave={(e) => {
                        if (lang !== code) e.target.style.background = 'transparent'
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
