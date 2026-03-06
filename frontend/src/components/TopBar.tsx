'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useTranslation } from 'react-i18next'
import '../i18n/config'

interface LangOption {
    code: string
    label: string
}

const LANG_OPTIONS: LangOption[] = [
    { code: 'en', label: 'EN' },
    { code: 'bn', label: 'বাং' },
    { code: 'hi', label: 'हि' },
]

export default function TopBar() {
    const { i18n } = useTranslation()
    const [currentLang, setCurrentLang] = useState(i18n.language || 'en')

    const switchLang = (code: string) => {
        i18n.changeLanguage(code)
        setCurrentLang(code)
    }

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800/60">
            <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2.5 group">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-sm shadow-lg shadow-blue-500/25">
                        WB
                    </div>
                    <div>
                        <div className="text-white font-bold text-sm leading-none">WB Digital Sahayak</div>
                        <div
                            className="text-slate-400 text-xs leading-none mt-0.5"
                            style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                        >
                            ডিজিটাল সহায়ক
                        </div>
                    </div>
                </Link>

                {/* Language switcher */}
                <div className="flex items-center gap-1 bg-slate-800/60 rounded-xl p-1 border border-slate-700/40">
                    {LANG_OPTIONS.map((lang) => (
                        <button
                            key={lang.code}
                            onClick={() => switchLang(lang.code)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${currentLang === lang.code
                                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/25'
                                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                                }`}
                            style={lang.code !== 'en' ? { fontFamily: "'Noto Sans Bengali', sans-serif" } : {}}
                        >
                            {lang.label}
                        </button>
                    ))}
                </div>
            </div>
        </nav>
    )
}
